"""
Section 3.2 of RFC 2812
<https://tools.ietf.org/html/rfc2812#section-3.2>
"""

from irctest import cases
from irctest.irc_utils.message_parser import Message

class JoinTestCase(cases.BaseServerTestCase):
    def testJoin(self):
        """“If a JOIN is successful, the user receives a JOIN message as
        confirmation and is then sent the channel's topic (using RPL_TOPIC) and
        the list of users who are on the channel (using RPL_NAMREPLY), which
        MUST include the user joining.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.1>

        “If a JOIN is successful, the user is then sent the channel's topic
        (using RPL_TOPIC) and the list of users who are on the channel (using
        RPL_NAMREPLY), which must include the user joining.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        """
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])
        m = self.getMessage(1)
        got_topic = False
        if m.command in ('331', '332'): # RPL_NOTOPIC, RPL_TOPIC
            got_topic = True
            m = self.getMessage(1)
            m = self.assertMessageEqual(m, command='353') # RPL_NAMREPLY
            m = self.getMessage(1)
            m = self.assertMessageEqual(m, command='366') # RPL_ENDOFNAMES
        else:
            m = self.assertMessageEqual(m, command='353') # RPL_NAMREPLY
            m = self.getMessage(1)
            m = self.assertMessageEqual(m, command='366') # RPL_ENDOFNAMES
            m = self.getMessage(1)
            self.assertIn(m.command, ('331', '332'), m) # RPL_NOTOPIC, RPL_TOPIC
    def testJoinTwice(self):
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])
        self.sendLine(1, 'JOIN #chan')
        # What should we do now?
