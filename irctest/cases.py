import socket
import unittest

from .irc_utils import message_parser

class _IrcTestCase(unittest.TestCase):
    controllerClass = None # Will be set by __main__.py

    def getLine(self):
        raise NotImplementedError()
    def getMessage(self, filter_pred=None):
        """Gets a message and returns it. If a filter predicate is given,
        fetches messages until the predicate returns a False on a message,
        and returns this message."""
        while True:
            msg = message_parser.parse_message(self.getLine())
            if not filter_pred or filter_pred(msg):
                return msg

class BaseClientTestCase(_IrcTestCase):
    """Basic class for client tests. Handles spawning a client and getting
    messages from it."""
    def setUp(self):
        self.controller = self.controllerClass()
        self._setUpServer()
    def tearDown(self):
        del self.controller
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
            print('C: {}'.format(line.strip()))
        return line
    def sendLine(self, line):
        assert self.conn.sendall(line.encode()) is None
        if not line.endswith('\r\n'):
            assert self.conn.sendall(b'\r\n') is None
        print('S: {}'.format(line.strip()))

class ClientNegociationHelper:
    """Helper class for tests handling capabilities negociation."""
    def readCapLs(self):
        (hostname, port) = self.server.getsockname()
        self.controller.run(
                hostname=hostname,
                port=port,
                authentication=None,
                )
        self.acceptClient()
        m = self.getMessage()
        self.assertEqual(m.command, 'CAP',
                'First message is not CAP LS.')
        if m.params == ['LS']:
            self.protocol_version = 301
        elif m.params == ['LS', '302']:
            self.protocol_version = 302
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
            self.nick = msg.params
            return False
        else:
            return True

    def negociateCapabilities(self, cap_ls):
        self.sendLine('CAP * LS :')
        while True:
            m = self.getMessage(filter_pred=self.userNickPredicate)
            self.assertEqual(m.command, 'CAP')
            self.assertGreater(len(m.params), 0, m)
            if m.params[0] == 'REQ':
                self.assertEqual(len(m.params), 2, m)
                requested = frozenset(m.params[1].split())
                if not requested.issubset(cap_ls):
                    self.sendLine('CAP * NAK :{}'.format(m.params[1])[0:100])
            else:
                return m

