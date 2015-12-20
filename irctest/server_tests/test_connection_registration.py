"""
Tests section 4.1 of RFC 1459.
<https://tools.ietf.org/html/rfc1459#section-4.1>
"""

from irctest import cases
from irctest import authentication
from irctest.irc_utils.message_parser import Message

class ConnectionRegistrationTestCase(cases.BaseServerTestCase):
    def connectClient(self, nick, name=None):
        name = self.addClient(name)
        self.sendLine(1, 'NICK {}'.format(nick))
        self.sendLine(1, 'USER username * * :Realname')

        # Skip to the point where we are registered
        # https://tools.ietf.org/html/rfc2812#section-3.1
        while True:
            m = self.getMessage(1)
            if m.command == '001':
                break
        self.sendLine(1, 'PING foo')

        # Skip all that happy welcoming stuff
        while True:
            m = self.getMessage(1)
            if m.command == 'PONG':
                break

    def testPassBeforeNickuser(self):
        """“Currently this requires that user send a PASS command before
        sending the NICK/USER combination.”
        <https://tools.ietf.org/html/rfc2812#section-3.1.1>"""
        self.connectClient('foo')
        self.getMessages(1)
        self.sendLine(1, 'PASS :foo')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='462') # ERR_ALREADYREGISTRED

    def testQuitDisconnects(self):
        """“The server must close the connection to a client which sends a
        QUIT message.” <https://tools.ietf.org/html/rfc1459#section-4.1.3>
        """
        self.connectClient('foo')
        self.getMessages(1)
        self.sendLine(1, 'QUIT')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='ERROR')
        self.assertDisconnected(1)

    def testNickCollision(self):
        self.connectClient('foo')
        self.addClient()
        self.sendLine(2, 'NICK foo')
        self.sendLine(2, 'USER username * * :Realname')
        m = self.getMessage(2, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertNotEqual(m.command, '001')

    def testEarlyNickCollision(self):
        self.addClient()
        self.addClient()
        self.sendLine(1, 'NICK foo')
        self.sendLine(2, 'NICK foo')
        self.sendLine(1, 'USER username * * :Realname')
        self.sendLine(2, 'USER username * * :Realname')
        m1 = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        m2 = self.getMessage(2, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertNotEqual((m1.command, m2.command), ('001', '001'))
