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
        received_commands = {m.command for m in self.getMessages(1)}
        expected_commands = {
                '353', # RPL_NAMREPLY
                '366', # RPL_ENDOFNAMES
                }
        self.assertTrue(expected_commands.issubset(received_commands),
                'Server sent {} commands, but at least {} were expected.'
                .format(received_commands, expected_commands))
        self.assertTrue(received_commands & {'331', '332'} != set(), # RPL_NOTOPIC, RPL_TOPIC
                'Server sent neither 331 (RPL_NOTOPIC) or 332 (RPL_TOPIC)')

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


    def testPartNotInEmptyChannel(self):
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

    def testPartNotInNonEmptyChannel(self):
        self.connectClient('foo')
        self.connectClient('bar')
        self.sendLine(1, 'JOIN #chan')
        self.sendLine(2, 'PART #chan')
        self.getMessages(1)
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='442') # ERR_NOTONCHANNEL

    def testJoinTwice(self):
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])
        self.sendLine(1, 'JOIN #chan')
        # What should we do now?
