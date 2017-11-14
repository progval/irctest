"""
Section 3.2 of RFC 2812
<https://tools.ietf.org/html/rfc2812#section-3.3>
"""

from irctest import cases
from irctest import client_mock
from irctest import runner
from irctest.irc_utils import ambiguities
from irctest.irc_utils.message_parser import Message

class PrivmsgTestCase(cases.BaseServerTestCase):
    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testPrivmsg(self):
        """<https://tools.ietf.org/html/rfc2812#section-3.3.1>"""
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        self.connectClient('bar')
        self.sendLine(2, 'JOIN #chan')
        self.sendLine(1, 'PRIVMSG #chan :hello there')
        self.getMessages(1) # synchronize
        pms = [msg for msg in self.getMessages(2) if msg.command == 'PRIVMSG']
        self.assertEqual(len(pms), 1)
        self.assertMessageEqual(
            pms[0],
            command='PRIVMSG',
            params=['#chan', 'hello there']
        )

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testPrivmsgNonexistentChannel(self):
        """<https://tools.ietf.org/html/rfc2812#section-3.3.1>"""
        self.connectClient('foo')
        self.sendLine(1, 'PRIVMSG #nonexistent :hello there')
        msg = self.getMessage(1)
        # ERR_NOSUCHNICK, ERR_NOSUCHCHANNEL, or ERR_CANNOTSENDTOCHAN
        self.assertIn(msg.command, ('401', '403', '404'))

class NoticeTestCase(cases.BaseServerTestCase):
    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testNotice(self):
        """<https://tools.ietf.org/html/rfc2812#section-3.3.2>"""
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        self.connectClient('bar')
        self.sendLine(2, 'JOIN #chan')
        self.sendLine(1, 'NOTICE #chan :hello there')
        self.getMessages(1) # synchronize
        notices = [msg for msg in self.getMessages(2) if msg.command == 'NOTICE']
        self.assertEqual(len(notices), 1)
        self.assertMessageEqual(
            notices[0],
            command='NOTICE',
            params=['#chan', 'hello there']
        )

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testNoticeNonexistentChannel(self):
        """
        'automatic replies MUST NEVER be sent in response to a NOTICE message'
        https://tools.ietf.org/html/rfc2812#section-3.3.2>
        """
        self.connectClient('foo')
        self.sendLine(1, 'NOTICE #nonexistent :hello there')
        self.assertEqual(self.getMessages(1), [])
