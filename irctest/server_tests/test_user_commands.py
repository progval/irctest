"""
User commands as specified in Section 3.6 of RFC 2812:
<https://tools.ietf.org/html/rfc2812#section-3.6>
"""

from irctest import cases

RPL_WHOISUSER = '311'
RPL_WHOISCHANNELS = '319'

class WhoisTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testWhoisUser(self):
        """Test basic WHOIS behavior"""
        nick = 'myCoolNickname'
        username = 'myCoolUsername'
        realname = 'My Real Name'
        self.addClient()
        self.sendLine(1, f'NICK {nick}')
        self.sendLine(1, f'USER {username} 0 * :{realname}')
        self.skipToWelcome(1)

        self.connectClient('otherNickname')
        self.getMessages(2)
        self.sendLine(2, 'WHOIS mycoolnickname')
        messages = self.getMessages(2)
        whois_user = messages[0]
        self.assertEqual(whois_user.command, RPL_WHOISUSER)
        #  "<client> <nick> <username> <host> * :<realname>"
        self.assertEqual(whois_user.params[1], nick)
        self.assertIn(whois_user.params[2], ('~' + username, '~' + username[0:9]))
        # dumb regression test for oragono/oragono#355:
        self.assertNotIn(whois_user.params[3], [nick, username, '~' + username, realname])
        self.assertEqual(whois_user.params[5], realname)
