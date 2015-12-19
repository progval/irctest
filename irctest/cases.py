import socket
import unittest

from .irc_utils import message_parser

class _IrcTestCase(unittest.TestCase):
    controllerClass = None # Will be set by __main__.py

class ClientTestCase(_IrcTestCase):
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
