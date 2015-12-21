import time
import socket
import unittest
import functools
import collections

from . import authentication
from . import optional_extensions
from .irc_utils import message_parser
from .irc_utils import capabilities

class ConnectionClosed(Exception):
    pass
class NoMessageException(AssertionError):
    pass

class _IrcTestCase(unittest.TestCase):
    """Base class for test cases."""
    controllerClass = None # Will be set by __main__.py

    def setUp(self):
        super().setUp()
        self.controller = self.controllerClass()
        self.inbuffer = []
        if self.show_io:
            print('---- new test ----')
    def assertMessageEqual(self, msg, subcommand=None, subparams=None,
            target=None, **kwargs):
        """Helper for partially comparing a message.

        Takes the message as first arguments, and comparisons to be made
        as keyword arguments.

        Deals with subcommands (eg. `CAP`) if any of `subcommand`,
        `subparams`, and `target` are given."""
        for (key, value) in kwargs.items():
            #with self.subTest(key=key):
                self.assertEqual(getattr(msg, key), value, msg)
        if subcommand is not None or subparams is not None:
            self.assertGreater(len(msg.params), 2, msg)
            msg_target = msg.params[0]
            msg_subcommand = msg.params[1]
            msg_subparams = msg.params[2:]
            if subcommand:
                with self.subTest(key='subcommand'):
                    self.assertEqual(msg_subcommand, subcommand, msg)
            if subparams is not None:
                with self.subTest(key='subparams'):
                    self.assertEqual(msg_subparams, subparams, msg)

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
    def acceptClient(self):
        """Make the server accept a client connection. Blocking."""
        (self.conn, addr) = self.server.accept()
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
    def readCapLs(self, auth=None):
        (hostname, port) = self.server.getsockname()
        self.controller.run(
                hostname=hostname,
                port=port,
                auth=auth,
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

class Client:
    def __init__(self, name, show_io):
        self.name = name
        self.show_io = show_io
        self.inbuffer = []
    def connect(self, hostname, port):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(1) # TODO: configurable
        self.conn.connect((hostname, port))
        if self.show_io:
            print('{:.3f} {}: connects to server.'.format(time.time(), self.name))
    def disconnect(self):
        if self.show_io:
            print('{:.3f} {}: disconnects from server.'.format(time.time(), self.name))
        self.conn.close()
    def getMessages(self, synchronize=True, assert_get_one=False):
        if synchronize:
            token = 'synchronize{}'.format(time.monotonic())
            self.sendLine('PING {}'.format(token))
        got_pong = False
        data = b''
        messages = []
        conn = self.conn
        while not got_pong:
            try:
                new_data = conn.recv(4096)
            except socket.timeout:
                if not assert_get_one and not synchronize and data == b'':
                    # Received nothing
                    return []
                if self.show_io:
                    print('{:.3f} waiting…'.format(time.time()))
                time.sleep(0.1)
                continue
            else:
                if not new_data:
                    # Connection closed
                    raise ConnectionClosed()
            data += new_data
            if not new_data.endswith(b'\r\n'):
                time.sleep(0.1)
                continue
            if not synchronize:
                got_pong = True
            for line in data.decode().split('\r\n'):
                if line:
                    if self.show_io:
                        print('{:.3f} S -> {}: {}'.format(time.time(), self.name, line.strip()))
                    message = message_parser.parse_message(line + '\r\n')
                    if message.command == 'PONG' and \
                            token in message.params:
                        got_pong = True
                    else:
                        messages.append(message)
            data = b''
        return messages
    def getMessage(self, filter_pred=None, synchronize=True):
        while True:
            if not self.inbuffer:
                self.inbuffer = self.getMessages(
                        synchronize=synchronize, assert_get_one=True)
            if not self.inbuffer:
                raise NoMessageException()
            message = self.inbuffer.pop(0) # TODO: use dequeue
            if not filter_pred or filter_pred(message):
                return message
    def sendLine(self, line):
        ret = self.conn.sendall(line.encode())
        assert ret is None
        if not line.endswith('\r\n'):
            ret = self.conn.sendall(b'\r\n')
            assert ret is None
        if self.show_io:
            print('{:.3f} {} -> S: {}'.format(time.time(), self.name, line.strip()))

class BaseServerTestCase(_IrcTestCase):
    """Basic class for server tests. Handles spawning a server and exchanging
    messages with it."""
    def setUp(self):
        super().setUp()
        self.find_hostname_and_port()
        self.controller.run(self.hostname, self.port)
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
        if not name:
            name = max(map(int, list(self.clients)+[0]))+1
        show_io = show_io if show_io is not None else self.show_io
        self.clients[name] = Client(name=name, show_io=show_io)
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
    def connectClient(self, nick, name=None):
        name = self.addClient(name)
        self.sendLine(1, 'NICK {}'.format(nick))
        self.sendLine(1, 'USER username * * :Realname')

        # Skip to the point where we are registered
        # https://tools.ietf.org/html/rfc2812#section-3.1
        while True:
            m = self.getMessage(1, synchronize=False)
            if m.command == '001':
                break
        self.sendLine(1, 'PING foo')

        # Skip all that happy welcoming stuff
        while True:
            m = self.getMessage(1)
            if m.command == 'PONG':
                break

class OptionalityHelper:
    def checkMechanismSupport(self, mechanism):
        if mechanism in self.controller.supported_sasl_mechanisms:
            return
        raise optional_extensions.OptionalSaslMechanismNotSupported(mechanism)

    def skipUnlessHasMechanism(mech):
        def decorator(f):
            @functools.wraps(f)
            def newf(self):
                self.checkMechanismSupport(mech)
                return f(self)
            return newf
        return decorator

