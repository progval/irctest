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
