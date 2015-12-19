import socket
import unittest

from .irc_utils import message_parser

class _IrcTestCase(unittest.TestCase):
    controllerClass = None # Will be set by __main__.py

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
        self.conn_file = self.conn.makefile(newline='\r\n')

    def getLine(self):
        return self.conn_file.readline().strip()
    def getMessage(self):
        return message_parser.parse_message(self.conn_file.readline())

class NegociationHelper:
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
        self.assertEqual(m.subcommand, 'LS',
                'First message is not CAP LS.')
        if m.params == []:
            self.protocol_version = 301
        elif m.params == ['302']:
            self.protocol_version = 302
        else:
            raise AssertionError('Unknown protocol version {}'
                    .format(m.params))
