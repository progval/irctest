import functools
import socket
import ssl
import tempfile
import time
from typing import Optional, Set
import unittest

import pytest

from . import basecontrollers, client_mock, runner
from .basecontrollers import TestCaseControllerConfig
from .exceptions import ConnectionClosed
from .irc_utils import capabilities, message_parser
from .irc_utils.junkdrawer import normalizeWhitespace
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


class ChannelJoinException(Exception):
    def __init__(self, code, params):
        super().__init__(f"Failed to join channel ({code}): {params}")
        self.code = code
        self.params = params


class _IrcTestCase(unittest.TestCase):
    """Base class for test cases."""

    controllerClass = None  # Will be set by __main__.py

    @staticmethod
    def config() -> TestCaseControllerConfig:
        """Some configuration to pass to the controllers.
        For example, Oragono only enables its MySQL support if
        config()["chathistory"]=True.
        """
        return TestCaseControllerConfig()

    def description(self):
        method_doc = self._testMethodDoc
        if not method_doc:
            return ""
        return "\t" + normalizeWhitespace(
            method_doc, removeNewline=False
        ).strip().replace("\n ", "\n\t")

    def setUp(self):
        super().setUp()
        self.controller = self.controllerClass(self.config())
        self.inbuffer = []
        if self.show_io:
            print("---- new test ----")

    def assertMessageEqual(self, msg, **kwargs):
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Uses self.listMatch on the params argument.
        """
        error = self.messageDiffers(msg, **kwargs)
        if error:
            raise self.failureException(error)

    def messageEqual(self, msg, **kwargs):
        """Boolean negation of `messageDiffers` (returns a boolean,
        not an optional string)."""
        return not self.messageDiffers(msg, **kwargs)

    def messageDiffers(
        self,
        msg,
        params=None,
        target=None,
        nick=None,
        fail_msg=None,
        extra_format=(),
        **kwargs,
    ):
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

        if params and not self.listMatch(msg.params, params):
            fail_msg = fail_msg or "params to be {expects}, got {got}: {msg}"
            return fail_msg.format(
                *extra_format, got=msg.params, expects=params, msg=msg
            )

        if nick:
            got_nick = msg.prefix.split("!")[0]
            if msg.prefix is None:
                fail_msg = (
                    fail_msg or "expected nick to be {expects}, got {got} prefix: {msg}"
                )
                return fail_msg.format(
                    *extra_format, got=got_nick, expects=nick, param=key, msg=msg
                )

        return None

    def listMatch(self, got, expected):
        """Returns True iff the list are equal.
        The ellipsis (aka. "..." aka triple dots) can be used on the 'expected'
        side as a wildcard, matching any *single* value."""
        if len(got) != len(expected):
            return False
        for (got_value, expected_value) in zip(got, expected):
            if expected_value is Ellipsis:
                # wildcard
                continue
            if got_value != expected_value:
                return False
        return True

    def assertIn(self, item, list_, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, item=item, list=list_, msg=msg)
        super().assertIn(item, list_, fail_msg)

    def assertNotIn(self, item, list_, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, item=item, list=list_, msg=msg)
        super().assertNotIn(item, list_, fail_msg)

    def assertEqual(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        super().assertEqual(got, expects, fail_msg)

    def assertNotEqual(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        super().assertNotEqual(got, expects, fail_msg)

    def assertGreater(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        super().assertGreater(got, expects, fail_msg)

    def assertGreaterEqual(
        self, got, expects, msg=None, fail_msg=None, extra_format=()
    ):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        super().assertGreaterEqual(got, expects, fail_msg)

    def assertLess(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        super().assertLess(got, expects, fail_msg)

    def assertLessEqual(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format, got=got, expects=expects, msg=msg)
        super().assertLessEqual(got, expects, fail_msg)


class BaseClientTestCase(_IrcTestCase):
    """Basic class for client tests. Handles spawning a client and exchanging
    messages with it."""

    nick = None
    user = None

    def setUp(self):
        super().setUp()
        self.conn = None
        self._setUpServer()

    def tearDown(self):
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

    def _setUpServer(self):
        """Creates the server and make it listen."""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("", 0))  # Bind any free port
        self.server.listen(1)

        # Used to check if the client is alive from time to time
        self.server.settimeout(1)

    def acceptClient(self, tls_cert=None, tls_key=None, server=None):
        """Make the server accept a client connection. Blocking."""
        server = server or self.server
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

    def getLine(self):
        line = self.conn_file.readline()
        if self.show_io:
            print("{:.3f} C: {}".format(time.time(), line.strip()))
        return line

    def getMessages(self, *args):
        lines = self.getLines(*args)
        return map(message_parser.parse_message, lines)

    def getMessage(self, *args, filter_pred=None):
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

    def sendLine(self, line):
        self.conn.sendall(line.encode())
        if not line.endswith("\r\n"):
            self.conn.sendall(b"\r\n")
        if self.show_io:
            print("{:.3f} S: {}".format(time.time(), line.strip()))


class ClientNegociationHelper:
    """Helper class for tests handling capabilities negociation."""

    def readCapLs(self, auth=None, tls_config=None):
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

    def userNickPredicate(self, msg):
        """Predicate to be used with getMessage to handle NICK/USER
        transparently."""
        if msg.command == "NICK":
            self.assertEqual(len(msg.params), 1, msg)
            self.nick = msg.params[0]
            return False
        elif msg.command == "USER":
            self.assertEqual(len(msg.params), 4, msg)
            self.user = msg.params
            return False
        else:
            return True

    def negotiateCapabilities(self, caps, cap_ls=True, auth=None):
        """Performes a complete capability negociation process, without
        ending it, so the caller can continue the negociation."""
        if cap_ls:
            self.readCapLs(auth)
            if not self.protocol_version:
                # No negotiation.
                return
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
                    self.acked_capabilities.update(requested)
            else:
                return m


class BaseServerTestCase(_IrcTestCase):
    """Basic class for server tests. Handles spawning a server and exchanging
    messages with it."""

    password: Optional[str] = None
    ssl = False
    valid_metadata_keys: Set[str] = set()
    invalid_metadata_keys: Set[str] = set()

    def setUp(self):
        super().setUp()
        self.server_support = None
        self.find_hostname_and_port()
        self.controller.run(
            self.hostname,
            self.port,
            password=self.password,
            valid_metadata_keys=self.valid_metadata_keys,
            invalid_metadata_keys=self.invalid_metadata_keys,
            ssl=self.ssl,
        )
        self.clients = {}

    def tearDown(self):
        self.controller.kill()
        for client in list(self.clients):
            self.removeClient(client)

    def find_hostname_and_port(self):
        """Find available hostname/port to listen on."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        (self.hostname, self.port) = s.getsockname()
        s.close()

    def addClient(self, name=None, show_io=None):
        """Connects a client to the server and adds it to the dict.
        If 'name' is not given, uses the lowest unused non-negative integer."""
        self.controller.wait_for_port()
        if not name:
            name = max(map(int, list(self.clients) + [0])) + 1
        show_io = show_io if show_io is not None else self.show_io
        self.clients[name] = client_mock.ClientMock(name=name, show_io=show_io)
        self.clients[name].connect(self.hostname, self.port)
        return name

    def removeClient(self, name):
        """Disconnects the client, without QUIT."""
        assert name in self.clients
        self.clients[name].disconnect()
        del self.clients[name]

    def getMessages(self, client, **kwargs):
        return self.clients[client].getMessages(**kwargs)

    def getMessage(self, client, **kwargs):
        return self.clients[client].getMessage(**kwargs)

    def getRegistrationMessage(self, client):
        """Filter notices, do not send pings."""
        return self.getMessage(
            client, synchronize=False, filter_pred=lambda m: m.command != "NOTICE"
        )

    def sendLine(self, client, line):
        return self.clients[client].sendLine(line)

    def getCapLs(self, client, as_list=False):
        """Waits for a CAP LS block, parses all CAP LS messages, and return
        the dict capabilities, with their values.

        If as_list is given, returns the raw list (ie. key/value not split)
        in case the order matters (but it shouldn't)."""
        caps = []
        while True:
            m = self.getRegistrationMessage(client)
            self.assertMessageEqual(m, command="CAP")
            self.assertEqual(m.params[1], "LS", fail_msg="Expected CAP * LS, got {got}")
            if m.params[2] == "*":
                caps.extend(m.params[3].split())
            else:
                caps.extend(m.params[2].split())
                if not as_list:
                    caps = capabilities.cap_list_to_dict(caps)
                return caps

    def assertDisconnected(self, client):
        try:
            self.getMessages(client)
            self.getMessages(client)
        except (socket.error, ConnectionClosed):
            del self.clients[client]
            return
        else:
            raise AssertionError("Client not disconnected.")

    def skipToWelcome(self, client):
        """Skip to the point where we are registered
        <https://tools.ietf.org/html/rfc2812#section-3.1>
        """
        result = []
        while True:
            m = self.getMessage(client, synchronize=False)
            result.append(m)
            if m.command == "001":
                return result

    def connectClient(
        self,
        nick,
        name=None,
        capabilities=None,
        skip_if_cap_nak=False,
        show_io=None,
        account=None,
        password=None,
        ident="username",
    ):
        client = self.addClient(name, show_io=show_io)
        if capabilities is not None and 0 < len(capabilities):
            self.sendLine(client, "CAP REQ :{}".format(" ".join(capabilities)))
            m = self.getRegistrationMessage(client)
            try:
                self.assertMessageEqual(
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
            self.sendLine(client, "CAP END")
        if password is not None:
            self.sendLine(client, "AUTHENTICATE PLAIN")
            self.sendLine(client, sasl_plain_blob(account or nick, password))
        self.sendLine(client, "NICK {}".format(nick))
        self.sendLine(client, "USER %s * * :Realname" % (ident,))

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
                    else:
                        (key, value) = (param, None)
                    self.server_support[key] = value
            welcome.append(m)

        return welcome

    def joinClient(self, client, channel):
        self.sendLine(client, "JOIN {}".format(channel))
        received = {m.command for m in self.getMessages(client)}
        self.assertIn(
            "366",
            received,
            fail_msg="Join to {} failed, {item} is not in the set of "
            "received responses: {list}",
            extra_format=(channel,),
        )

    def joinChannel(self, client, channel):
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


class OptionalityHelper:
    controller: basecontrollers.BaseServerController

    def checkSaslSupport(self):
        if self.controller.supported_sasl_mechanisms:
            return
        raise runner.NotImplementedByController("SASL")

    def checkMechanismSupport(self, mechanism):
        if mechanism in self.controller.supported_sasl_mechanisms:
            return
        raise runner.OptionalSaslMechanismNotSupported(mechanism)

    @staticmethod
    def skipUnlessHasMechanism(mech):
        def decorator(f):
            @functools.wraps(f)
            def newf(self):
                self.checkMechanismSupport(mech)
                return f(self)

            return newf

        return decorator

    def skipUnlessHasSasl(f):
        @functools.wraps(f)
        def newf(self):
            self.checkSaslSupport()
            return f(self)

        return newf


def mark_specifications(*specifications, deprecated=False, strict=False):
    specifications = frozenset(
        Specifications.from_name(s) if isinstance(s, str) else s for s in specifications
    )
    if None in specifications:
        raise ValueError("Invalid set of specifications: {}".format(specifications))

    def decorator(f):
        for specification in specifications:
            f = getattr(pytest.mark, specification.value)(f)
        if strict:
            f = pytest.mark.strict(f)
        if deprecated:
            f = pytest.mark.deprecated(f)
        return f

    return decorator


def mark_capabilities(*capabilities, deprecated=False, strict=False):
    capabilities = frozenset(
        Capabilities.from_name(c) if isinstance(c, str) else c for c in capabilities
    )
    if None in capabilities:
        raise ValueError("Invalid set of capabilities: {}".format(capabilities))

    def decorator(f):
        for capability in capabilities:
            f = getattr(pytest.mark, capability.value)(f)
        # Support for any capability implies IRCv3
        f = pytest.mark.IRCv3(f)
        return f

    return decorator


def mark_isupport(*tokens, deprecated=False, strict=False):
    tokens = frozenset(
        IsupportTokens.from_name(c) if isinstance(c, str) else c for c in tokens
    )
    if None in tokens:
        raise ValueError("Invalid set of isupport tokens: {}".format(tokens))

    def decorator(f):
        for token in tokens:
            f = getattr(pytest.mark, token.value)(f)
        return f

    return decorator
