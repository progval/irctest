"""
Tests section 4.1 of RFC 1459.
<https://tools.ietf.org/html/rfc1459#section-4.1>
"""

from irctest import cases
from irctest import authentication
from irctest.irc_utils.message_parser import Message
from irctest.basecontrollers import NotImplementedByController

class PasswordedConnectionRegistrationTestCase(cases.BaseServerTestCase):
    password = 'testpassword'
    def testPassBeforeNickuser(self):
        self.addClient()
        self.sendLine(1, 'PASS {}'.format(self.password))
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'USER username * * :Realname')

        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='001')

    def testNoPassword(self):
        self.addClient()
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'USER username * * :Realname')
        m = self.getRegistrationMessage(1)
        self.assertNotEqual(m.command, '001')

    def testPassAfterNickuser(self):
        """“The password can and must be set before any attempt to register
        the connection is made.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.1.1>

        “The optional password can and MUST be set before any attempt to
        register the connection is made.
        Currently this requires that user send a PASS command before
        sending the NICK/USER combination.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.1.1>
        """
        self.addClient()
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'USER username * * :Realname')
        self.sendLine(1, 'PASS {}'.format(self.password))
        m = self.getRegistrationMessage(1)
        self.assertNotEqual(m.command, '001')

class ConnectionRegistrationTestCase(cases.BaseServerTestCase):
    def testQuitDisconnects(self):
        """“The server must close the connection to a client which sends a
        QUIT message.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.1.3>
        """
        self.connectClient('foo')
        self.getMessages(1)
        self.sendLine(1, 'QUIT')
        self.assertRaises(cases.ConnectionClosed, self.getMessages, 1)

    def testNickCollision(self):
        """A user connects and requests the same nickname as an already
        registered user.
        """
        self.connectClient('foo')
        self.addClient()
        self.sendLine(2, 'NICK foo')
        self.sendLine(2, 'USER username * * :Realname')
        m = self.getRegistrationMessage(2)
        self.assertNotEqual(m.command, '001')

    def testEarlyNickCollision(self):
        """Two users register simultaneously with the same nick."""
        self.addClient()
        self.addClient()
        self.sendLine(1, 'NICK foo')
        self.sendLine(2, 'NICK foo')
        self.sendLine(1, 'USER username * * :Realname')
        self.sendLine(2, 'USER username * * :Realname')
        m1 = self.getRegistrationMessage(1)
        m2 = self.getRegistrationMessage(2)
        self.assertNotEqual((m1.command, m2.command), ('001', '001'))
