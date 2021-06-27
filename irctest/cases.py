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
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
import unittest

import pytest

from . import basecontrollers, client_mock, patma, runner, tls
from .authentication import Authentication
from .basecontrollers import TestCaseControllerConfig
from .exceptions import ConnectionClosed
from .irc_utils import capabilities, message_parser
from .irc_utils.junkdrawer import find_hostname_and_port, normalizeWhitespace
from .irc_utils.message_parser import Message
from .irc_utils.sasl import sasl_plain_blob
from .numerics import (
    ERR_BADCHANNELKEY,
    ERR_BANNEDFROMCHAN,
    ERR_INVITEONLYCHAN,
    ERR_NEEDREGGEDNICK,
    ERR_NOSUCHCHANNEL,
    ERR_TOOMANYCHANNELS,
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
    ]
)

# typevar for decorators
TCallable = TypeVar("TCallable", bound=Callable)

# typevar for the client name used by tests (usually int or str)
TClientName = TypeVar("TClientName", bound=Union[Hashable, int])

TController = TypeVar("TController", bound=basecontrollers._BaseController)

# general-purpose typevar
T = TypeVar("T")


class ChannelJoinException(Exception):
    def __init__(self, code: str, params: List[str]):
        super().__init__(f"Failed to join channel ({code}): {params}")
        self.code = code
        self.params = params


class _IrcTestCase(unittest.TestCase, Generic[TController]):
    """Base class for test cases."""

    # Will be set by __main__.py
    controllerClass: Type[TController]
    show_io: bool

    controller: TController

    @staticmethod
    def config() -> TestCaseControllerConfig:
        """Some configuration to pass to the controllers.
        For example, Oragono only enables its MySQL support if
        config()["chathistory"]=True.
        """
        return TestCaseControllerConfig()

    def description(self) -> str:
        method_doc = self._testMethodDoc
        if not method_doc:
            return ""
        return "\t" + normalizeWhitespace(
            method_doc, removeNewline=False
        ).strip().replace("\n ", "\n\t")

    def setUp(self) -> None:
        super().setUp()
        if self.controllerClass is not None:
            self.controller = self.controllerClass(self.config())
        if self.show_io:
            print("---- new test ----")

    def assertMessageMatch(self, msg: Message, **kwargs: Any) -> None:
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Uses patma.match_list on the params argument.
        """
        error = self.messageDiffers(msg, **kwargs)
        if error:
            raise self.failureException(error)

    def messageEqual(self, msg: Message, **kwargs: Any) -> bool:
        """Boolean negation of `messageDiffers` (returns a boolean,
        not an optional string)."""
        return not self.messageDiffers(msg, **kwargs)

    def messageDiffers(
        self,
        msg: Message,
        params: Optional[List[Union[str, None, patma.Operator]]] = None,
        target: Optional[str] = None,
        tags: Optional[
            Dict[Union[str, patma.Operator], Union[str, patma.Operator, None]]
        ] = None,
        nick: Optional[str] = None,
        fail_msg: Optional[str] = None,
        extra_format: Tuple = (),
        **kwargs: Any,
    ) -> Optional[str]:
        """Returns an error message if the message doesn't match the given arguments,
        or None if it matches."""
        for (key, value) in kwargs.items():
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

        if params and not patma.match_list(list(msg.params), params):
            fail_msg = (
                fail_msg or "expected params to match {expects}, got {got}: {msg}"
            )
            return fail_msg.format(
                *extra_format, got=msg.params, expects=params, msg=msg
            )

        if tags and not patma.match_dict(msg.tags, tags):
            fail_msg = fail_msg or "expected tags to match {expects}, got {got}: {msg}"
            return fail_msg.format(*extra_format, got=msg.tags, expects=tags, msg=msg)

        if nick:
            got_nick = msg.prefix.split("!")[0] if msg.prefix else None
            if nick != got_nick:
                fail_msg = (
                    fail_msg
                    or "expected nick to be {expects}, got {got} instead: {msg}"
                )
                return fail_msg.format(
                    *extra_format, got=got_nick, expects=nick, param=key, msg=msg
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
        super().assertIn(member, container, msg)

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
        super().assertNotIn(member, container, msg)

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
        super().assertEqual(got, expects, msg)

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
        super().assertNotEqual(got, expects, msg)

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
        super().assertGreater(got, expects, msg)

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
        super().assertGreaterEqual(got, expects, msg)

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
        super().assertLess(got, expects, msg)

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
        super().assertLessEqual(got, expects, msg)


class BaseClientTestCase(_IrcTestCase[basecontrollers.BaseClientController]):
    """Basic class for client tests. Handles spawning a client and exchanging
    messages with it."""

    conn: Optional[socket.socket]
    nick: Optional[str] = None
    user: Optional[List[str]] = None
    server: socket.socket
    protocol_version = Optional[str]
    acked_capabilities = Optional[Set[str]]

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
            msg = message_parser.parse_message(line)
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
        self, auth: Optional[Authentication] = None, tls_config: tls.TlsConfig = None
    ) -> None:
        (hostname, port) = self.server.getsockname()
        self.controller.run(
            hostname=hostname, port=port, auth=auth, tls_config=tls_config
        )
        self.acceptClient()
        m = self.getMessage()
        self.assertEqual(m.command, "CAP", "First message is not CAP LS.")
        if m.params == ["LS"]:
            self.protocol_version = 301
        elif m.params == ["LS", "302"]:
            self.protocol_version = 302
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
    valid_metadata_keys: Set[str] = set()
    invalid_metadata_keys: Set[str] = set()
    server_support: Optional[Dict[str, Optional[str]]]

    def setUp(self) -> None:
        super().setUp()
        self.server_support = None
        (self.hostname, self.port) = find_hostname_and_port()
        self.controller.run(
            self.hostname,
            self.port,
            password=self.password,
            valid_metadata_keys=self.valid_metadata_keys,
            invalid_metadata_keys=self.invalid_metadata_keys,
            ssl=self.ssl,
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
        if not name:
            new_name: int = (
                max(
                    [int(name) for name in self.clients if isinstance(name, (int, str))]
                    + [0]
                )
                + 1
            )
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
        return self.clients[client].getMessages(**kwargs)

    def getMessage(self, client: TClientName, **kwargs: Any) -> Message:
        return self.clients[client].getMessage(**kwargs)

    def getRegistrationMessage(self, client: TClientName) -> Message:
        """Filter notices, do not send pings."""
        return self.getMessage(
            client, synchronize=False, filter_pred=lambda m: m.command != "NOTICE"
        )

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
            if skip_if_cap_nak:
                raise runner.CapabilityNotSupported(" or ".join(capabilities))
            else:
                raise

    def connectClient(
        self,
        nick: str,
        name: TClientName = None,
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
            m = self.getRegistrationMessage(client)
            self.requestCapabilities(client, capabilities, skip_if_cap_nak)
        if password is not None:
            if "sasl" not in (capabilities or ()):
                raise ValueError("Used 'password' option without sasl capbilitiy")
            self.sendLine(client, "AUTHENTICATE PLAIN")
            m = self.getRegistrationMessage(client)
            self.assertMessageMatch(m, command="AUTHENTICATE", params=["+"])
            self.sendLine(client, sasl_plain_blob(account or nick, password))
            m = self.getRegistrationMessage(client)
            self.assertIn(m.command, ["900", "903"], str(m))

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


_TSelf = TypeVar("_TSelf", bound="OptionalityHelper")
_TReturn = TypeVar("_TReturn")


class OptionalityHelper(Generic[TController]):
    controller: TController

    def checkSaslSupport(self) -> None:
        if self.controller.supported_sasl_mechanisms:
            return
        raise runner.NotImplementedByController("SASL")

    def checkMechanismSupport(self, mechanism: str) -> None:
        if mechanism in self.controller.supported_sasl_mechanisms:
            return
        raise runner.OptionalSaslMechanismNotSupported(mechanism)

    @staticmethod
    def skipUnlessHasMechanism(
        mech: str,
    ) -> Callable[[Callable[[_TSelf], _TReturn]], Callable[[_TSelf], _TReturn]]:
        # Just a function returning a function that takes functions and
        # returns functions, nothing to see here.
        # If Python didn't have such an awful syntax for callables, it would be:
        # str -> ((TSelf -> TReturn) -> (TSelf -> TReturn))
        def decorator(f: Callable[[_TSelf], _TReturn]) -> Callable[[_TSelf], _TReturn]:
            @functools.wraps(f)
            def newf(self: _TSelf) -> _TReturn:
                self.checkMechanismSupport(mech)
                return f(self)

            return newf

        return decorator

    @staticmethod
    def skipUnlessHasSasl(
        f: Callable[[_TSelf], _TReturn]
    ) -> Callable[[_TSelf], _TReturn]:
        @functools.wraps(f)
        def newf(self: _TSelf) -> _TReturn:
            self.checkSaslSupport()
            return f(self)

        return newf


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
