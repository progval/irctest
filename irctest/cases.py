import ssl
import time
import socket
import tempfile
import unittest
import functools
import collections

import supybot.utils

from . import runner
from . import client_mock
from . import authentication
from .irc_utils import capabilities
from .irc_utils import message_parser
from .exceptions import ConnectionClosed
from .specifications import Specifications

class _IrcTestCase(unittest.TestCase):
    """Base class for test cases."""
    controllerClass = None # Will be set by __main__.py

    def description(self):
        method_doc = self._testMethodDoc
        if not method_doc:
            return ''
        return '\t'+supybot.utils.str.normalizeWhitespace(
                method_doc,
                removeNewline=False,
                ).strip().replace('\n ', '\n\t')

    def setUp(self):
        super().setUp()
        self.controller = self.controllerClass()
        self.inbuffer = []
        if self.show_io:
            print('---- new test ----')
    def assertMessageEqual(self, msg, subcommand=None, subparams=None,
            target=None, nick=None, fail_msg=None, extra_format=(),
            strip_first_param=False, **kwargs):
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Deals with subcommands (eg. `CAP`) if any of `subcommand`,
        `subparams`, and `target` are given."""
        fail_msg = fail_msg or '{msg}'
        for (key, value) in kwargs.items():
            if strip_first_param and key == 'params':
                value = value[1:]
            self.assertEqual(getattr(msg, key), value, msg, fail_msg,
                    extra_format=extra_format)
        if nick:
            self.assertNotEqual(msg.prefix, None, msg, fail_msg)
            self.assertEqual(msg.prefix.split('!')[0], nick, msg, fail_msg)
        if subcommand is not None or subparams is not None:
            self.assertGreater(len(msg.params), 2, fail_msg)
            msg_target = msg.params[0]
            msg_subcommand = msg.params[1]
            msg_subparams = msg.params[2:]
            if subcommand:
                self.assertEqual(msg_subcommand, subcommand, msg, fail_msg,
                        extra_format=extra_format)
            if subparams is not None:
                self.assertEqual(msg_subparams, subparams, msg, fail_msg,
                        extra_format=extra_format)

    def assertIn(self, item, list_, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format,
                    item=item, list=list_, msg=msg)
        super().assertIn(item, list_, fail_msg)
    def assertNotIn(self, item, list_, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format,
                    item=item, list=list_, msg=msg)
        super().assertNotIn(item, list_, fail_msg)
    def assertEqual(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format,
                    got=got, expects=expects, msg=msg)
        super().assertEqual(got, expects, fail_msg)
    def assertNotEqual(self, got, expects, msg=None, fail_msg=None, extra_format=()):
        if fail_msg:
            fail_msg = fail_msg.format(*extra_format,
                    got=got, expects=expects, msg=msg)
        super().assertNotEqual(got, expects, fail_msg)

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
            self.conn.sendall(b'QUIT :end of test.')
        self.controller.kill()
        if self.conn:
            self.conn_file.close()
            self.conn.close()
        self.server.close()

    def _setUpServer(self):
        """Creates the server and make it listen."""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('', 0)) # Bind any free port
        self.server.listen(1)
    def acceptClient(self, tls_cert=None, tls_key=None):
        """Make the server accept a client connection. Blocking."""
        (self.conn, addr) = self.server.accept()
        if tls_cert is None and tls_key is None:
            pass
        else:
            assert tls_cert and tls_key, \
                'tls_cert must be provided if and only if tls_key is.'
            with tempfile.NamedTemporaryFile('at') as certfile, \
                    tempfile.NamedTemporaryFile('at') as keyfile:
                certfile.write(tls_cert)
                certfile.seek(0)
                keyfile.write(tls_key)
                keyfile.seek(0)
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(certfile=certfile.name, keyfile=keyfile.name)
                self.conn = context.wrap_socket(self.conn, server_side=True)
        self.conn_file = self.conn.makefile(newline='\r\n',
                encoding='utf8')

    def getLine(self):
        line = self.conn_file.readline()
        if self.show_io:
            print('{:.3f} C: {}'.format(time.time(), line.strip()))
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
        ret = self.conn.sendall(line.encode())
        assert ret is None
        if not line.endswith('\r\n'):
            ret = self.conn.sendall(b'\r\n')
            assert ret is None
        if self.show_io:
            print('{:.3f} S: {}'.format(time.time(), line.strip()))

class ClientNegociationHelper:
    """Helper class for tests handling capabilities negociation."""
    def readCapLs(self, auth=None, tls_config=None):
        (hostname, port) = self.server.getsockname()
        self.controller.run(
                hostname=hostname,
                port=port,
                auth=auth,
                tls_config=tls_config,
                )
        self.acceptClient()
        m = self.getMessage()
        self.assertEqual(m.command, 'CAP',
                'First message is not CAP LS.')
        if m.params == ['LS']:
            self.protocol_version = 301
        elif m.params == ['LS', '302']:
            self.protocol_version = 302
        elif m.params == ['END']:
            self.protocol_version = None
        else:
            raise AssertionError('Unknown CAP params: {}'
                    .format(m.params))

    def userNickPredicate(self, msg):
        """Predicate to be used with getMessage to handle NICK/USER
        transparently."""
        if msg.command == 'NICK':
            self.assertEqual(len(msg.params), 1, msg)
            self.nick = msg.params[0]
            return False
        elif msg.command == 'USER':
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
            self.sendLine('CAP * LS :{}'.format(' '.join(caps)))
        capability_names = frozenset(capabilities.cap_list_to_dict(caps))
        self.acked_capabilities = set()
        while True:
            m = self.getMessage(filter_pred=self.userNickPredicate)
            if m.command != 'CAP':
                return m
            self.assertGreater(len(m.params), 0, m)
            if m.params[0] == 'REQ':
                self.assertEqual(len(m.params), 2, m)
                requested = frozenset(m.params[1].split())
                if not requested.issubset(capability_names):
                    self.sendLine('CAP {} NAK :{}'.format(
                        self.nick or '*',
                        m.params[1][0:100]))
                else:
                    self.sendLine('CAP {} ACK :{}'.format(
                        self.nick or '*',
                        m.params[1]))
                    self.acked_capabilities.update(requested)
            else:
                return m


class BaseServerTestCase(_IrcTestCase):
    """Basic class for server tests. Handles spawning a server and exchanging
    messages with it."""
    password = None
    ssl = False
    valid_metadata_keys = frozenset()
    invalid_metadata_keys = frozenset()
    def setUp(self):
        super().setUp()
        self.server_support = {}
        self.find_hostname_and_port()
        self.controller.run(self.hostname, self.port, password=self.password,
                valid_metadata_keys=self.valid_metadata_keys,
                invalid_metadata_keys=self.invalid_metadata_keys,
                ssl=self.ssl)
        self.clients = {}
    def tearDown(self):
        self.controller.kill()
        for client in list(self.clients):
            self.removeClient(client)
    def find_hostname_and_port(self):
        """Find available hostname/port to listen on."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        (self.hostname, self.port) = s.getsockname()
        s.close()

    def addClient(self, name=None, show_io=None):
        """Connects a client to the server and adds it to the dict.
        If 'name' is not given, uses the lowest unused non-negative integer."""
        self.controller.wait_for_port()
        if not name:
            name = max(map(int, list(self.clients)+[0]))+1
        show_io = show_io if show_io is not None else self.show_io
        self.clients[name] = client_mock.ClientMock(name=name,
                show_io=show_io)
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
        return self.getMessage(client, synchronize=False,
                filter_pred=lambda m:m.command != 'NOTICE')
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
            self.assertMessageEqual(m, command='CAP', subcommand='LS')
            if m.params[2] == '*':
                caps.extend(m.params[3].split())
            else:
                caps.extend(m.params[2].split())
                if not as_list:
                    caps = capabilities.cap_list_to_dict(caps)
                return caps

    def assertDisconnected(self, client):
        try:
            self.getLines(client)
            self.sendLine(client, 'PING foo')
            while True:
                l = self.getLine(client)
                self.assertNotEqual(line, '')
                m = message_parser.parse_message(l)
                self.assertNotEqual(m.command, 'PONG',
                        'Client not disconnected.')
        except socket.error:
            del self.clients[client]
            return
        else:
            raise AssertionError('Client not disconnected.')


    def skipToWelcome(self, client):
        """Skip to the point where we are registered
        <https://tools.ietf.org/html/rfc2812#section-3.1>
        """
        while True:
            m = self.getMessage(client, synchronize=False)
            if m.command == '001':
                return m
    def connectClient(self, nick, name=None, capabilities=None,
            skip_if_cap_nak=False):
        client = self.addClient(name)
        if capabilities is not None and 0 < len(capabilities):
            self.sendLine(client, 'CAP REQ :{}'.format(' '.join(capabilities)))
            m = self.getRegistrationMessage(client)
            try:
                self.assertMessageEqual(m, command='CAP',
                        fail_msg='Expected CAP ACK, got: {msg}')
                self.assertEqual(m.params[1], 'ACK', m,
                        fail_msg='Expected CAP ACK, got: {msg}')
            except AssertionError:
                if skip_if_cap_nak:
                    raise runner.NotImplementedByController(
                            ', '.join(capabilities))
                else:
                    raise
            self.sendLine(client, 'CAP END')
        self.sendLine(client, 'NICK {}'.format(nick))
        self.sendLine(client, 'USER username * * :Realname')

        self.skipToWelcome(client)
        self.sendLine(client, 'PING foo')

        # Skip all that happy welcoming stuff
        while True:
            m = self.getMessage(client)
            if m.command == 'PONG':
                break
            elif m.command == '005':
                for param in m.params[1:-1]:
                    if '=' in param:
                        (key, value) = param.split('=')
                    else:
                        (key, value) = (param, None)
                    self.server_support[key] = value

    def joinClient(self, client, channel):
        self.sendLine(client, 'JOIN {}'.format(channel))
        received = {m.command for m in self.getMessages(client)}
        self.assertIn('366', received,
                fail_msg='Join to {} failed, {item} is not in the set of '
                'received responses: {list}',
                extra_format=(channel,))

    def joinChannel(self, client, channel):
        self.sendLine(client, 'JOIN {}'.format(channel))
        # wait until we see them join the channel
        joined = False
        while not joined:
            for msg in self.getMessages(client):
                # todo: also respond to cannot join channel numeric
                if msg.command.upper() == 'JOIN' and 0 < len(msg.params) and msg.params[0].lower() == channel.lower():
                    joined = True
                    break

class OptionalityHelper:
    def checkSaslSupport(self):
        if self.controller.supported_sasl_mechanisms:
            return
        raise runner.NotImplementedByController('SASL')

    def checkMechanismSupport(self, mechanism):
        if mechanism in self.controller.supported_sasl_mechanisms:
            return
        raise runner.OptionalSaslMechanismNotSupported(mechanism)

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

class SpecificationSelector:

    def requiredBySpecification(*specifications, strict=False):
        specifications = frozenset(
                Specifications.of_name(s) if isinstance(s, str) else s
                for s in specifications)
        if None in specifications:
            raise ValueError('Invalid set of specifications: {}'
                    .format(specifications))
        def decorator(f):
            @functools.wraps(f)
            def newf(self):
                if specifications.isdisjoint(self.testedSpecifications):
                    raise runner.NotRequiredBySpecifications()
                if strict and not self.strictTests:
                    raise runner.SkipStrictTest()
                return f(self)
            return newf
        return decorator
