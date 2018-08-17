"""
User commands as specified in Section 3.6 of RFC 2812:
<https://tools.ietf.org/html/rfc2812#section-3.6>
"""

from irctest import cases

RPL_WHOISCHANNELS = '319'

class InvisibleTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testInvisibleWhois(self):
        """Test interaction between MODE +i and RPL_WHOISCHANNELS."""
        self.connectClient('userOne')
        self.sendLine(1, 'JOIN #xyz')

        self.connectClient('userTwo')
        self.getMessages(2)
        self.sendLine(2, 'WHOIS userOne')
        commands = {m.command for m in self.getMessages(2)}
        self.assertIn(RPL_WHOISCHANNELS, commands,
             'RPL_WHOISCHANNELS should be sent for a non-invisible nick')

        self.getMessages(1)
        self.sendLine(1, 'MODE userOne +i')
        message = self.getMessage(1)
        self.assertEqual(message.command, 'MODE',
            'Expected MODE reply, but received {}'.format(message.command))
        self.assertEqual(message.params, ['userOne', '+i'],
            'Expected user set +i, but received {}'.format(message.params))

        self.getMessages(2)
        self.sendLine(2, 'WHOIS userOne')
        commands = {m.command for m in self.getMessages(2)}
        self.assertNotIn(RPL_WHOISCHANNELS, commands,
            'RPL_WHOISCHANNELS should not be sent for an invisible nick'
            'unless the user is also a member of the channel')

        self.sendLine(2, 'JOIN #xyz')
        self.sendLine(2, 'WHOIS userOne')
        commands = {m.command for m in self.getMessages(2)}
        self.assertIn(RPL_WHOISCHANNELS, commands,
             'RPL_WHOISCHANNELS should be sent for an invisible nick'
             'if the user is also a member of the channel')

        self.sendLine(2, 'PART #xyz')
        self.getMessages(2)
        self.getMessages(1)
        self.sendLine(1, 'MODE userOne -i')
        message = self.getMessage(1)
        self.assertEqual(message.command, 'MODE',
            'Expected MODE reply, but received {}'.format(message.command))
        self.assertEqual(message.params, ['userOne', '-i'],
            'Expected user set -i, but received {}'.format(message.params))

        self.sendLine(2, 'WHOIS userOne')
        commands = {m.command for m in self.getMessages(2)}
        self.assertIn(RPL_WHOISCHANNELS, commands,
             'RPL_WHOISCHANNELS should be sent for a non-invisible nick')

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testWhoisAccount(self):
        """Test numeric 330, RPL_WHOISACCOUNT."""
        self.controller.registerUser(self, 'shivaram', 'sesame')
        self.connectClient('netcat')
        self.sendLine(1, 'NS IDENTIFY shivaram sesame')
        self.getMessages(1)

        self.connectClient('curious')
        self.sendLine(2, 'WHOIS netcat')
        messages = self.getMessages(2)
        # 330 RPL_WHOISACCOUNT
        whoisaccount = [message for message in messages if message.command == '330']
        self.assertEqual(len(whoisaccount), 1)
        params = whoisaccount[0].params
        # <client> <nick> <authname> :<info>
        self.assertEqual(len(params), 4)
        self.assertEqual(params[:3], ['curious', 'netcat', 'shivaram'])

        self.sendLine(1, 'WHOIS curious')
        messages = self.getMessages(2)
        whoisaccount = [message for message in messages if message.command == '330']
        self.assertEqual(len(whoisaccount), 0)
