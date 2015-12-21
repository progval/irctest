"""
Section 3.2 of RFC 2812
<https://tools.ietf.org/html/rfc2812#section-3.2>
"""

from irctest import cases
from irctest.irc_utils import ambiguities
from irctest.irc_utils.message_parser import Message

class JoinTestCase(cases.BaseServerTestCase):
    def testJoinAllMessages(self):
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
        try:
            self.assertMessageEqual(m, command='JOIN', params=['#chan'])
        except AssertionError:
            pass
        else:
            m = self.getMessage(1)
        if m.command in ('331', '332'): # RPL_NOTOPIC, RPL_TOPIC
            m = self.getMessage(1)
            self.assertMessageEqual(m, command='353') # RPL_NAMREPLY
            m = self.getMessage(1)
            self.assertMessageEqual(m, command='366') # RPL_ENDOFNAMES
        else:
            self.assertMessageEqual(m, command='353') # RPL_NAMREPLY
            m = self.getMessage(1)
            self.assertMessageEqual(m, command='366') # RPL_ENDOFNAMES
            m = self.getMessage(1)
            self.assertIn(m.command, ('331', '332'), m) # RPL_NOTOPIC, RPL_TOPIC

    def testJoinNamreply(self):
        """“353    RPL_NAMREPLY
            "( "=" / "*" / "@" ) <channel>
             :[ "@" / "+" ] <nick> *( " " [ "@" / "+" ] <nick> )”
        -- <https://tools.ietf.org/html/rfc2812#section-5.2>
        """
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')

        for m in self.getMessages(1):
            if m.command == '353':
                self.assertIn(len(m.params), (3, 4), m)
                params = ambiguities.normalize_namreply_params(m.params)
                self.assertIn(params[1], '=*@', m)
                self.assertEqual(params[2], '#chan', m)
                self.assertIn(params[3], {'foo', '@foo', '+foo'}, m)


    def testPartNotInChannel(self):
        """“442     ERR_NOTONCHANNEL
            "<channel> :You're not on that channel"

        - Returned by the server whenever a client tries to
          perform a channel effecting command for which the
          client isn't a member.”
          -- <https://tools.ietf.org/html/rfc1459#section-6.1>
          and <https://tools.ietf.org/html/rfc2812#section-5.2>

        According to RFCs, ERR_NOSUCHCHANNEL should only be used for invalid
        channel names:
        “403     ERR_NOSUCHCHANNEL
          "<channel name> :No such channel"

        - Used to indicate the given channel name is invalid.”
        -- <https://tools.ietf.org/html/rfc1459#section-6.1>
        and <https://tools.ietf.org/html/rfc2812#section-5.2>

        However, many implementations use 479 instead, so let's allow it.
        <http://danieloaks.net/irc-defs/defs/ircnumerics.html#403>
        <http://danieloaks.net/irc-defs/defs/ircnumerics.html#479>
        """
        self.connectClient('foo')
        self.sendLine(1, 'PART #chan')
        m = self.getMessage(1)
        self.assertIn(m.command, {'442', '403'}) # ERR_NOTONCHANNEL, ERR_NOSUCHCHANNEL

    def testJoinTwice(self):
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])
        self.sendLine(1, 'JOIN #chan')
        # What should we do now?
