from irctest import cases
from irctest.irc_utils.sasl import sasl_plain_blob

from irctest.numerics import RPL_WELCOME
from irctest.numerics import ERR_NICKNAMEINUSE

class Bouncer(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testBouncer(self):
        """Test basic bouncer functionality."""
        self.controller.registerUser(self, 'observer', 'observerpassword')
        self.controller.registerUser(self, 'testuser', 'mypassword')

        self.connectClient('observer')
        self.joinChannel(1, '#chan')
        self.sendLine(1, 'NICKSERV IDENTIFY observer observerpassword')
        self.getMessages(1)

        self.addClient()
        self.sendLine(2, 'CAP LS 302')
        self.sendLine(2, 'AUTHENTICATE PLAIN')
        self.sendLine(2, sasl_plain_blob('testuser', 'mypassword'))
        self.sendLine(2, 'NICK testnick')
        self.sendLine(2, 'USER a 0 * a')
        self.sendLine(2, 'CAP REQ :server-time message-tags oragono.io/bnc')
        self.sendLine(2, 'CAP END')
        messages = self.getMessages(2)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 1)
        # should see a regburst for testnick
        self.assertEqual(welcomes[0].params[0], 'testnick')
        self.joinChannel(2, '#chan')

        self.addClient()
        self.sendLine(3, 'CAP LS 302')
        self.sendLine(3, 'AUTHENTICATE PLAIN')
        self.sendLine(3, sasl_plain_blob('testuser', 'mypassword'))
        self.sendLine(3, 'NICK testnick')
        self.sendLine(3, 'USER a 0 * a')
        self.sendLine(3, 'CAP REQ :server-time message-tags account-tag oragono.io/bnc')
        self.sendLine(3, 'CAP END')
        messages = self.getMessages(3)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 1)
        # should see the *same* regburst for testnick
        self.assertEqual(welcomes[0].params[0], 'testnick')
        joins = [message for message in messages if message.command == 'JOIN']
        # we should be automatically joined to #chan
        self.assertEqual(joins[0].params[0], '#chan')

        self.addClient()
        self.sendLine(4, 'CAP LS 302')
        self.sendLine(4, 'AUTHENTICATE PLAIN')
        self.sendLine(4, sasl_plain_blob('testuser', 'mypassword'))
        self.sendLine(4, 'NICK testnick')
        self.sendLine(4, 'USER a 0 * a')
        self.sendLine(4, 'CAP REQ :server-time message-tags')
        self.sendLine(4, 'CAP END')
        # without the bnc cap, we should not be able to attach to the nick
        messages = self.getMessages(4)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 0)
        errors = [message for message in messages if message.command == ERR_NICKNAMEINUSE]
        self.assertEqual(len(errors), 1)

        self.sendLine(1, '@+clientOnlyTag=Value PRIVMSG #chan :hey')
        self.getMessages(1)
        messagesfortwo = [msg for msg in self.getMessages(2) if msg.command == 'PRIVMSG']
        messagesforthree = [msg for msg in self.getMessages(3) if msg.command == 'PRIVMSG']
        self.assertEqual(len(messagesfortwo), 1)
        self.assertEqual(len(messagesforthree), 1)
        messagefortwo = messagesfortwo[0]
        messageforthree = messagesforthree[0]
        self.assertEqual(messagefortwo.params, ['#chan', 'hey'])
        self.assertEqual(messageforthree.params, ['#chan', 'hey'])
        self.assertIn('time', messagefortwo.tags)
        self.assertNotIn('account', messagefortwo.tags)
        self.assertIn('time', messageforthree.tags)
        # 3 has account-tag, 2 doesn't
        self.assertIn('account', messageforthree.tags)
        # should get same msgid
        self.assertEqual(messagefortwo.tags['msgid'], messageforthree.tags['msgid'])

        self.sendLine(2, 'QUIT :two out')
        quitLines = [msg for msg in self.getMessages(2) if msg.command == 'QUIT']
        self.assertEqual(len(quitLines), 1)
        self.assertIn('two out', quitLines[0].params[0])
        # neither the observer nor the other attached session should see a quit here
        quitLines = [msg for msg in self.getMessages(1) if msg.command == 'QUIT']
        self.assertEqual(quitLines, [])
        quitLines = [msg for msg in self.getMessages(3) if msg.command == 'QUIT']
        self.assertEqual(quitLines, [])

        # session 3 should be untouched at this point
        self.sendLine(1, '@+clientOnlyTag=Value PRIVMSG #chan :hey again')
        self.getMessages(1)
        messagesforthree = [msg for msg in self.getMessages(3) if msg.command == 'PRIVMSG']
        self.assertEqual(len(messagesforthree), 1)
        self.assertMessageEqual(messagesforthree[0], command='PRIVMSG', params=['#chan', 'hey again'])

        self.sendLine(3, 'QUIT :three out')
        quitLines = [msg for msg in self.getMessages(3) if msg.command == 'QUIT']
        self.assertEqual(len(quitLines), 1)
        self.assertIn('three out', quitLines[0].params[0])
        # observer should see *this* quit
        quitLines = [msg for msg in self.getMessages(1) if msg.command == 'QUIT']
        self.assertEqual(len(quitLines), 1)
        self.assertIn('three out', quitLines[0].params[0])
