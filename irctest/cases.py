import contextlib
import functools
import socket
import ssl
import tempfile
import time
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    Generic,
    Hashable,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import pytest

from . import basecontrollers, client_mock, patma, runner, tls
from .authentication import Authentication
from .basecontrollers import TestCaseControllerConfig
from .exceptions import ConnectionClosed
from .irc_utils import capabilities, message_parser
from .irc_utils.message_parser import Message
from .irc_utils.sasl import sasl_plain_blob
from .numerics import (
    ERR_BADCHANNELKEY,
    ERR_BANNEDFROMCHAN,
    ERR_CHANNELISFULL,
    ERR_INVITEONLYCHAN,
    ERR_NEEDREGGEDNICK,
    ERR_NOSUCHCHANNEL,
    ERR_TOOMANYCHANNELS,
    RPL_HELLO,
)
from .specifications import Capabilities, IsupportTokens, Specifications

__tracebackhide__ = True  # Hide from pytest tracebacks on test failure.

CHANNEL_JOIN_FAIL_NUMERICS = frozenset(
    [
        ERR_NOSUCHCHANNEL,
        ERR_TOOMANYCHANNELS,
        ERR_BADCHANNELKEY,
        ERR_INVITEONLYCHAN,
        ERR_BANNEDFROMCHAN,
        ERR_NEEDREGGEDNICK,
        ERR_CHANNELISFULL,
    ]
)

# typevar for decorators
TCallable = TypeVar("TCallable", bound=Callable)
TClass = TypeVar("TClass", bound=Type)

# typevar for the client name used by tests (usually int or str)
TClientName = TypeVar("TClientName", bound=Union[Hashable, int])

TController = TypeVar("TController", bound=basecontrollers._BaseController)

# general-purpose typevar
T = TypeVar("T")


def retry(f: TCallable) -> TCallable:
    """Retry the function if it raises ConnectionClosed; as a workaround for flaky
    connection, such as::

        1: connects to server.
        1 -> S: NICK foo
        1 -> S: USER username * * :Realname
        S -> 1: :My.Little.Server NOTICE * :*** Found your hostname (cached)
        S -> 1: :My.Little.Server NOTICE * :*** Checking Ident
        S -> 1: :My.Little.Server NOTICE * :*** No Ident response
        S -> 1: ERROR :Closing Link: cpu-pool.com (Use a different port)
    """

    @functools.wraps(f)
    def newf(*args, **kwargs):  # type: ignore
        try:
            return f(*args, **kwargs)
        except ConnectionClosed:
            time.sleep(1)
            return f(*args, **kwargs)

    return newf  # type: ignore


class ChannelJoinException(Exception):
    def __init__(self, code: str, params: List[str]):
        super().__init__(f"Failed to join channel ({code}): {params}")
        self.code = code
        self.params = params


class _IrcTestCase(Generic[TController]):
    """Base class for test cases.

    It implements various `assert*` method that look like unittest's,
    but is actually based on the `assert` statement so derived classes are
    pytest-style rather than unittest-style.

    It also calls setUp() and tearDown() like unittest would."""

    # Will be set by __main__.py
    controllerClass: Type[TController]
    show_io: bool

    controller: TController

    __new__ = object.__new__  # pytest won't collect Generic subclasses otherwise

    @staticmethod
    def config() -> TestCaseControllerConfig:
        """Some configuration to pass to the controllers.
        For example, Ergo only enables its MySQL support if
        config()["chathistory"]=True.
        """
        return TestCaseControllerConfig()

    def setUp(self) -> None:
        if self.controllerClass is not None:
            self.controller = self.controllerClass(self.config())
        if self.show_io:
            print("---- new test ----")

    def tearDown(self) -> None:
        pass

    def setup_method(self, method: Callable) -> None:
        self.setUp()

    def teardown_method(self, method: Callable) -> None:
        self.tearDown()

    def assertMessageMatch(self, msg: Message, **kwargs: Any) -> None:
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Uses patma.match_list on the params argument.
        """
        error = self.messageDiffers(msg, **kwargs)
        if error:
            raise AssertionError(error)

    def messageEqual(self, msg: Message, **kwargs: Any) -> bool:
        """Boolean negation of `messageDiffers` (returns a boolean,
        not an optional string)."""
        return not self.messageDiffers(msg, **kwargs)

    def messageDiffers(
        self,
        msg: Message,
        command: Union[str, None, patma.Operator] = None,
        params: Optional[List[Union[str, None, patma.Operator]]] = None,
        target: Optional[str] = None,
        tags: Optional[
            Dict[Union[str, patma.Operator], Union[str, patma.Operator, None]]
        ] = None,
        nick: Optional[str] = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
        prefix: Union[None, str, patma.Operator] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Returns an error message if the message doesn't match the given arguments,
        or None if it matches."""
        for key, value in kwargs.items():
            if getattr(msg, key) != value:
                fail_msg = (
                    fail_msg or "expected {param} to be {expects}, got {got}: {msg}"
                )
                return fail_msg.format(
                    *extra_format,
                    got=getattr(msg, key),
                    expects=value,
                    param=key,
                    msg=msg,
                )

        if command is not None and not patma.match_string(msg.command, command):
            fail_msg = (
                fail_msg or "expected command to match {expects}, got {got}: {msg}"
            )
            return fail_msg.format(
                *extra_format, got=msg.command, expects=command, msg=msg
            )

        if prefix is not None and not patma.match_string(msg.prefix, prefix):
            fail_msg = (
                fail_msg or "expected prefix to match {expects}, got {got}: {msg}"
            )
            return fail_msg.format(
                *extra_format, got=msg.prefix, expects=prefix, msg=msg
            )

        if params is not None and not patma.match_list(list(msg.params), params):
            fail_msg = (
                fail_msg or "expected params to match {expects}, got {got}: {msg}"
            )
            return fail_msg.format(
                *extra_format, got=msg.params, expects=params, msg=msg
            )

        if tags is not None and not patma.match_dict(msg.tags, tags):
            fail_msg = fail_msg or "expected tags to match {expects}, got {got}: {msg}"
            return fail_msg.format(*extra_format, got=msg.tags, expects=tags, msg=msg)

        if nick is not None:
            got_nick = msg.prefix.split("!")[0] if msg.prefix else None
            if nick != got_nick:
                fail_msg = (
                    fail_msg
                    or "expected nick to be {expects}, got {got} instead: {msg}"
                )
                return fail_msg.format(
                    *extra_format, got=got_nick, expects=nick, msg=msg
                )

        return None

    def assertIn(
        self,
        member: Any,
        container: Union[Iterable[Any], Container[Any]],
        msg: Optional[str] = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, item=member, list=container, msg=msg)
        assert member in container, msg  # type: ignore

    def assertNotIn(
        self,
        member: Any,
        container: Union[Iterable[Any], Container[Any]],
        msg: Optional[str] = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, item=member, list=container, msg=msg)
        assert member not in container, msg  # type: ignore

    def assertEqual(
        self,
        got: T,
        expects: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got == expects, msg

    def assertNotEqual(
        self,
        got: T,
        expects: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got != expects, msg

    def assertGreater(
        self,
        got: T,
        expects: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got > expects, msg  # type: ignore

    def assertGreaterEqual(
        self,
        got: T,
        expects: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got >= expects, msg  # type: ignore

    def assertLess(
        self,
        got: T,
        expects: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got < expects, msg  # type: ignore

    def assertLessEqual(
        self,
        got: T,
        expects: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        assert got <= expects, msg  # type: ignore

    def assertTrue(
        self,
        got: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, msg=msg)
        assert got, msg

    def assertFalse(
        self,
        got: T,
        msg: Any = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
    ) -> None:
        if fail_msg:
            msg = fail_msg.format(*extra_format, got=got, msg=msg)
        assert not got, msg

    @contextlib.contextmanager
    def assertRaises(self, exception: Type[Exception]) -> Iterator[None]:
        with pytest.raises(exception):
            yield


class BaseClientTestCase(_IrcTestCase[basecontrollers.BaseClientController]):
    """Basic class for client tests. Handles spawning a client and exchanging
    messages with it."""

    conn: Optional[socket.socket]
    nick: Optional[str] = None
    user: Optional[List[str]] = None
    server: socket.socket
    protocol_version: Optional[str]
    acked_capabilities: Optional[Set[str]]

    __new__ = object.__new__  # pytest won't collect Generic[] subclasses otherwise

    def setUp(self) -> None:
        super().setUp()
        self.conn = None
        self._setUpServer()

    def tearDown(self) -> None:
        if self.conn:
            try:
                self.conn.sendall(b"QUIT :end of test.")
            except BrokenPipeError:
                pass  # client already disconnected
            except OSError:
                pass  # the conn was already closed by the test, or something
        self.controller.kill()
        if self.conn:
            self.conn_file.close()
            self.conn.close()
        self.server.close()

    def _setUpServer(self) -> None:
        """Creates the server and make it listen."""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("", 0))  # Bind any free port
        self.server.listen(1)

        # Used to check if the client is alive from time to time
        self.server.settimeout(1)

    def acceptClient(
        self,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        server: Optional[socket.socket] = None,
    ) -> None:
        """Make the server accept a client connection. Blocking."""
        server = server or self.server
        assert server
        # Wait for the client to connect
        while True:
            try:
                (self.conn, addr) = server.accept()
            except socket.timeout:
                self.controller.check_is_alive()
            else:
                break
        if tls_cert is None and tls_key is None:
            pass
        else:
            assert (
                tls_cert and tls_key
            ), "tls_cert must be provided if and only if tls_key is."
            with tempfile.NamedTemporaryFile(
                "at"
            ) as certfile, tempfile.NamedTemporaryFile("at") as keyfile:
                certfile.write(tls_cert)
                certfile.seek(0)
                keyfile.write(tls_key)
                keyfile.seek(0)
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=certfile.name, keyfile=keyfile.name)
                self.conn = context.wrap_socket(self.conn, server_side=True)
        self.conn_file = self.conn.makefile(newline="\r\n", encoding="utf8")

    def getLine(self) -> str:
        line = self.conn_file.readline()
        if self.show_io:
            print("{:.3f} C: {}".format(time.time(), line.strip()))
        return line

    def getMessage(
        self, *args: Any, filter_pred: Optional[Callable[[Message], bool]] = None
    ) -> Message:
        """Gets a message and returns it. If a filter predicate is given,
        fetches messages until the predicate returns a False on a message,
        and returns this message."""
        while True:
            line = self.getLine(*args)
            if not line:
                raise ConnectionClosed()
            # strip final "\r\n", then parse
            msg = message_parser.parse_message(line[:-2])
            if not filter_pred or filter_pred(msg):
                return msg

    def sendLine(self, line: str) -> None:
        assert self.conn
        self.conn.sendall(line.encode())
        if not line.endswith("\r\n"):
            self.conn.sendall(b"\r\n")
        if self.show_io:
            print("{:.3f} S: {}".format(time.time(), line.strip()))

    def readCapLs(
        self,
        auth: Optional[Authentication] = None,
        tls_config: Optional[tls.TlsConfig] = None,
    ) -> None:
        (hostname, port) = self.server.getsockname()
        self.controller.run(
            hostname=hostname, port=port, auth=auth, tls_config=tls_config
        )
        self.acceptClient()
        m = self.getMessage()
        self.assertEqual(m.command, "CAP", "First message is not CAP LS.")
        if m.params == ["LS"]:
            self.protocol_version = "301"
        elif m.params == ["LS", "302"]:
            self.protocol_version = "302"
        elif m.params == ["END"]:
            self.protocol_version = None
        else:
            raise AssertionError("Unknown CAP params: {}".format(m.params))

    def userNickPredicate(self, msg: Message) -> bool:
        """Predicate to be used with getMessage to handle NICK/USER
        transparently."""
        if msg.command == "NICK":
            self.assertEqual(len(msg.params), 1, msg=msg)
            self.nick = msg.params[0]
            return False
        elif msg.command == "USER":
            self.assertEqual(len(msg.params), 4, msg=msg)
            self.user = msg.params
            return False
        else:
            return True

    def negotiateCapabilities(
        self,
        caps: List[str],
        cap_ls: bool = True,
        auth: Optional[Authentication] = None,
    ) -> Optional[Message]:
        """Performes a complete capability negociation process, without
        ending it, so the caller can continue the negociation."""
        if cap_ls:
            self.readCapLs(auth)
            if not self.protocol_version:
                # No negotiation.
                return None
            self.sendLine("CAP * LS :{}".format(" ".join(caps)))
        capability_names = frozenset(capabilities.cap_list_to_dict(caps))
        self.acked_capabilities = set()
        while True:
            m = self.getMessage(filter_pred=self.userNickPredicate)
            if m.command != "CAP":
                return m
            self.assertGreater(len(m.params), 0, m)
            if m.params[0] == "REQ":
                self.assertEqual(len(m.params), 2, m)
                requested = frozenset(m.params[1].split())
                if not requested.issubset(capability_names):
                    self.sendLine(
                        "CAP {} NAK :{}".format(self.nick or "*", m.params[1][0:100])
                    )
                else:
                    self.sendLine(
                        "CAP {} ACK :{}".format(self.nick or "*", m.params[1])
                    )
                    self.acked_capabilities.update(requested)  # type: ignore
            else:
                return m


class BaseServerTestCase(
    _IrcTestCase[basecontrollers.BaseServerController], Generic[TClientName]
):
    """Basic class for server tests. Handles spawning a server and exchanging
    messages with it."""

    show_io: bool  # set by conftest.py

    password: Optional[str] = None
    ssl = False
    server_support: Optional[Dict[str, Optional[str]]]
    run_services = False

    faketime: Optional[str] = None
    """If not None and the controller supports it and libfaketime is available,
    runs the server using faketime and this value set as the $FAKETIME env variable.
    Tests must check ``self.controller.faketime_enabled`` is True before
    relying on this."""

    __new__ = object.__new__  # pytest won't collect Generic[] subclasses otherwise

    def setUp(self) -> None:
        super().setUp()
        self.server_support = None
        (self.hostname, self.port) = self.controller.get_hostname_and_port()
        self.controller.run(
            self.hostname,
            self.port,
            password=self.password,
            ssl=self.ssl,
            run_services=self.run_services,
            faketime=self.faketime,
        )
        self.clients: Dict[TClientName, client_mock.ClientMock] = {}

    def tearDown(self) -> None:
        self.controller.kill()
        for client in list(self.clients):
            self.removeClient(client)

    def addClient(
        self, name: Optional[TClientName] = None, show_io: Optional[bool] = None
    ) -> TClientName:
        """Connects a client to the server and adds it to the dict.
        If 'name' is not given, uses the lowest unused non-negative integer."""
        self.controller.wait_for_port()
        if self.run_services:
            self.controller.wait_for_services()
        if not name:
            used_ids: List[int] = [
                int(name) for name in self.clients if isinstance(name, (int, str))
            ]
            new_name = max(used_ids + [0]) + 1
            name = cast(TClientName, new_name)
        show_io = show_io if show_io is not None else self.show_io
        self.clients[name] = client_mock.ClientMock(name=name, show_io=show_io)
        self.clients[name].connect(self.hostname, self.port)
        return name

    def removeClient(self, name: TClientName) -> None:
        """Disconnects the client, without QUIT."""
        assert name in self.clients
        self.clients[name].disconnect()
        del self.clients[name]

    def getMessages(self, client: TClientName, **kwargs: Any) -> List[Message]:
        if kwargs.get("synchronize", True):
            time.sleep(self.controller.sync_sleep_time)
        return self.clients[client].getMessages(**kwargs)

    def getMessage(self, client: TClientName, **kwargs: Any) -> Message:
        if kwargs.get("synchronize", True):
            time.sleep(self.controller.sync_sleep_time)
        return self.clients[client].getMessage(**kwargs)

    def getRegistrationMessage(self, client: TClientName) -> Message:
        """Filter notices, do not send pings."""
        while True:
            msg = self.getMessage(
                client,
                synchronize=False,
                filter_pred=lambda m: m.command not in ("NOTICE", RPL_HELLO),
            )
            if msg.command == "PING":
                # Hi Unreal
                self.sendLine(client, "PONG :" + msg.params[0])
            else:
                return msg

    def sendLine(self, client: TClientName, line: Union[str, bytes]) -> None:
        return self.clients[client].sendLine(line)

    def getCapLs(
        self, client: TClientName, as_list: bool = False
    ) -> Union[List[str], Dict[str, Optional[str]]]:
        """Waits for a CAP LS block, parses all CAP LS messages, and return
        the dict capabilities, with their values.

        If as_list is given, returns the raw list (ie. key/value not split)
        in case the order matters (but it shouldn't)."""
        caps = []
        while True:
            m = self.getRegistrationMessage(client)
            self.assertMessageMatch(m, command="CAP")
            self.assertEqual(m.params[1], "LS", fail_msg="Expected CAP * LS, got {got}")
            if m.params[2] == "*":
                caps.extend(m.params[3].split())
            else:
                caps.extend(m.params[2].split())
                if not as_list:
                    return capabilities.cap_list_to_dict(caps)
                return caps

    def assertDisconnected(self, client: TClientName) -> None:
        try:
            self.getMessages(client)
            self.getMessages(client)
        except (socket.error, ConnectionClosed):
            del self.clients[client]
            return
        else:
            raise AssertionError("Client not disconnected.")

    def skipToWelcome(self, client: TClientName) -> List[Message]:
        """Skip to the point where we are registered
        <https://tools.ietf.org/html/rfc2812#section-3.1>
        """
        result = []
        while True:
            m = self.getMessage(client, synchronize=False)
            result.append(m)
            if m.command == "001":
                return result
            elif m.command == "PING":
                # Hi, Unreal
                self.sendLine(client, "PONG :" + m.params[0])

    def requestCapabilities(
        self,
        client: TClientName,
        capabilities: List[str],
        skip_if_cap_nak: bool = False,
    ) -> None:
        self.sendLine(client, "CAP REQ :{}".format(" ".join(capabilities)))
        m = self.getRegistrationMessage(client)
        try:
            self.assertMessageMatch(
                m, command="CAP", fail_msg="Expected CAP ACK, got: {msg}"
            )
            self.assertEqual(
                m.params[1], "ACK", m, fail_msg="Expected CAP ACK, got: {msg}"
            )
        except AssertionError:
            # if skip_if_cap_nak, and any one of the capabilities is not
            # in the controller's required set, then skip the test;
            # otherwise fail
            if skip_if_cap_nak and any(
                not self.controller.supports_cap(cap) for cap in capabilities
            ):
                raise runner.CapabilityNotSupported(" or ".join(capabilities))
            else:
                raise

    def authenticateClient(
        self, client: TClientName, account: str, password: str
    ) -> None:
        self.sendLine(client, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(client)
        self.assertMessageMatch(m, command="AUTHENTICATE", params=["+"])
        self.sendLine(client, sasl_plain_blob(account, password))
        m = self.getRegistrationMessage(client)
        self.assertIn(m.command, ["900", "903"], str(m))

    @retry
    def connectClient(
        self,
        nick: str,
        name: Optional[TClientName] = None,
        capabilities: Optional[List[str]] = None,
        skip_if_cap_nak: bool = False,
        show_io: Optional[bool] = None,
        account: Optional[str] = None,
        password: Optional[str] = None,
        ident: str = "username",
    ) -> List[Message]:
        """Connections a new client, does the cap negotiation
        and connection registration, and skips to the end of the MOTD.
        Returns the list of all messages received after registration,
        just like `skipToWelcome`."""
        client = self.addClient(name, show_io=show_io)
        if capabilities:
            self.sendLine(client, "CAP LS 302")
            self.getCapLs(client)
            self.requestCapabilities(client, capabilities, skip_if_cap_nak)
        if password is not None:
            if "sasl" not in (capabilities or ()):
                raise ValueError("Used 'password' option without sasl capbilitiy")
            self.authenticateClient(client, account or nick, password)

        self.sendLine(client, "NICK {}".format(nick))
        self.sendLine(client, "USER %s * * :Realname" % (ident,))
        if capabilities:
            self.sendLine(client, "CAP END")

        welcome = self.skipToWelcome(client)
        self.sendLine(client, "PING foo")

        # Skip all that happy welcoming stuff
        self.server_support = {}
        while True:
            m = self.getMessage(client)
            if m.command == "PONG":
                break
            elif m.command == "005":
                for param in m.params[1:-1]:
                    if "=" in param:
                        (key, value) = param.split("=")
                        self.server_support[key] = value
                    else:
                        self.server_support[param] = None
            welcome.append(m)

        self.targmax: Dict[str, Optional[str]] = dict(  # type: ignore[assignment]
            item.split(":", 1)
            for item in (self.server_support.get("TARGMAX") or "").split(",")
            if item
        )

        return welcome

    def joinClient(self, client: TClientName, channel: str) -> None:
        self.sendLine(client, "JOIN {}".format(channel))
        received = {m.command for m in self.getMessages(client)}
        self.assertIn(
            "366",
            received,
            fail_msg="Join to {} failed, {item} is not in the set of "
            "received responses: {list}",
            extra_format=(channel,),
        )

    def joinChannel(self, client: TClientName, channel: str) -> None:
        self.sendLine(client, "JOIN {}".format(channel))
        # wait until we see them join the channel
        joined = False
        while not joined:
            for msg in self.getMessages(client):
                if (
                    msg.command == "JOIN"
                    and 0 < len(msg.params)
                    and msg.params[0].lower() == channel.lower()
                ):
                    joined = True
                    break
                elif msg.command in CHANNEL_JOIN_FAIL_NUMERICS:
                    raise ChannelJoinException(msg.command, msg.params)

    def getBatchMessages(
        self, client: TClientName, batch_type: str
    ) -> tuple[str, List[str], List[Message]]:
        """Extract messages from a batch, verifying batch markers.

        Args:
            client: The client to get messages from
            batch_type: The expected batch type (e.g., "metadata", "chathistory")

        Returns:
            A tuple of (batch_id, batch_params, messages) where:
            - batch_id is the batch identifier
            - batch_params is the list of parameters after the batch type
            - messages are the messages between the batch start and end markers
        """
        messages = self.getMessages(client)

        first_msg = messages.pop(0)
        last_msg = messages.pop(-1)
        self.assertMessageMatch(
            first_msg,
            command="BATCH",
        )

        # Verify batch type matches
        if len(first_msg.params) < 2 or first_msg.params[1] != batch_type:
            raise AssertionError(
                f"Expected batch type {batch_type!r}, got {first_msg.params[1] if len(first_msg.params) > 1 else 'none'}"
            )

        batch_id = first_msg.params[0][1:]  # Remove the '+' prefix
        batch_params = first_msg.params[2:]  # Everything after batch type

        self.assertMessageMatch(last_msg, command="BATCH", params=["-" + batch_id])

        return (batch_id, batch_params, messages)


_TSelf = TypeVar("_TSelf", bound="_IrcTestCase")
_TReturn = TypeVar("_TReturn")


def skipUnlessHasMechanism(
    mech: str,
) -> Callable[[Callable[..., _TReturn]], Callable[..., _TReturn]]:
    # Just a function returning a function that takes functions and
    # returns functions, nothing to see here.
    # If Python didn't have such an awful syntax for callables, it would be:
    # str -> ((TSelf -> TReturn) -> (TSelf -> TReturn))
    def decorator(f: Callable[..., _TReturn]) -> Callable[..., _TReturn]:
        @functools.wraps(f)
        def newf(self: _TSelf, *args: Any, **kwargs: Any) -> _TReturn:
            if mech not in self.controller.supported_sasl_mechanisms:
                raise runner.OptionalSaslMechanismNotSupported(mech)
            return f(self, *args, **kwargs)

        return newf

    return decorator


def xfailIf(
    condition: Callable[..., bool], reason: str
) -> Callable[[Callable[..., _TReturn]], Callable[..., _TReturn]]:
    # Works about the same as skipUnlessHasMechanism
    def decorator(f: Callable[..., _TReturn]) -> Callable[..., _TReturn]:
        @functools.wraps(f)
        def newf(self: _TSelf, *args: Any, **kwargs: Any) -> _TReturn:
            if condition(self, *args, **kwargs):
                try:
                    return f(self, *args, **kwargs)
                except Exception:
                    pytest.xfail(reason)
                    assert False  # make mypy happy
            else:
                return f(self, *args, **kwargs)

        return newf

    return decorator


def xfailIfSoftware(
    names: List[str], reason: str
) -> Callable[[Callable[..., _TReturn]], Callable[..., _TReturn]]:
    def pred(testcase: _IrcTestCase, *args: Any, **kwargs: Any) -> bool:
        return testcase.controller.software_name in names

    return xfailIf(pred, reason)


def mark_services(cls: TClass) -> TClass:
    cls.run_services = True
    return pytest.mark.services(cls)  # type: ignore


def mark_specifications(
    *specifications_str: str, deprecated: bool = False, strict: bool = False
) -> Callable[[TCallable], TCallable]:
    specifications = frozenset(
        Specifications.from_name(s) if isinstance(s, str) else s
        for s in specifications_str
    )
    if None in specifications:
        raise ValueError("Invalid set of specifications: {}".format(specifications))

    def decorator(f: TCallable) -> TCallable:
        for specification in specifications:
            f = getattr(pytest.mark, specification.value)(f)
        if strict:
            f = pytest.mark.strict(f)
        if deprecated:
            f = pytest.mark.deprecated(f)
        return f

    return decorator


def mark_capabilities(
    *capabilities_str: str, deprecated: bool = False, strict: bool = False
) -> Callable[[TCallable], TCallable]:
    capabilities = frozenset(
        Capabilities.from_name(c) if isinstance(c, str) else c for c in capabilities_str
    )
    if None in capabilities:
        raise ValueError("Invalid set of capabilities: {}".format(capabilities))

    def decorator(f: TCallable) -> TCallable:
        for capability in capabilities:
            f = getattr(pytest.mark, capability.value)(f)
        # Support for any capability implies IRCv3
        f = pytest.mark.IRCv3(f)
        return f

    return decorator


def mark_isupport(
    *tokens_str: str, deprecated: bool = False, strict: bool = False
) -> Callable[[TCallable], TCallable]:
    tokens = frozenset(
        IsupportTokens.from_name(c) if isinstance(c, str) else c for c in tokens_str
    )
    if None in tokens:
        raise ValueError("Invalid set of isupport tokens: {}".format(tokens))

    def decorator(f: TCallable) -> TCallable:
        for token in tokens:
            f = getattr(pytest.mark, token.value)(f)
        return f

    return decorator
