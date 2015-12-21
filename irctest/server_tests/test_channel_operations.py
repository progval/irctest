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

        This test makes a user join and check what is sent to them.
        """
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')

        for m in self.getMessages(1):
            if m.command == '353':
                self.assertIn(len(m.params), (3, 4), m,
                        fail_msg='RPL_NAM_REPLY with number of arguments '
                        '<3 or >4: {msg}')
                params = ambiguities.normalize_namreply_params(m.params)
                self.assertIn(params[1], '=*@', m,
                        fail_msg='Bad channel prefix: {got} not in {expects}: {msg}')
                self.assertEqual(params[2], '#chan', m,
                        fail_msg='Bad channel name: {got} instead of '
                        '{expects}: {msg}')
                self.assertIn(params[3], {'foo', '@foo', '+foo'}, m,
                        fail_msg='Bad user list: should contain only user '
                        '"foo" with an optional "+" or "@" prefix, but got: '
                        '{msg}')


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
        self.assertIn(m.command, {'442', '403'}, m, # ERR_NOTONCHANNEL, ERR_NOSUCHCHANNEL
                fail_msg='Expected ERR_NOTONCHANNEL (442) or '
                'ERR_NOSUCHCHANNEL (403) after PARTing an empty channel '
                'one is not on, but got: {msg}')

    def testPartNotInNonEmptyChannel(self):
        self.connectClient('foo')
        self.connectClient('bar')
        self.sendLine(1, 'JOIN #chan')
        self.getMessages(1) # Synchronize
        self.sendLine(2, 'PART #chan')
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='442', # ERR_NOTONCHANNEL
                fail_msg='Expected ERR_NOTONCHANNEL (442) '
                'after PARTing a non-empty channel '
                'one is not on, but got: {msg}')
        self.assertEqual(self.getMessages(2), [])
    testPartNotInNonEmptyChannel.__doc__ = testPartNotInEmptyChannel.__doc__

    def testJoinTwice(self):
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])
        self.getMessages(1)
        self.sendLine(1, 'JOIN #chan')
        # Note that there may be no message. Both RFCs require replies only
        # if the join is successful, or has an error among the given set.
        for m in self.getMessages(1):
            if m.command == '353':
                self.assertIn(len(m.params), (3, 4), m,
                        fail_msg='RPL_NAM_REPLY with number of arguments '
                        '<3 or >4: {msg}')
                params = ambiguities.normalize_namreply_params(m.params)
                self.assertIn(params[1], '=*@', m,
                        fail_msg='Bad channel prefix: {got} not in {expects}: {msg}')
                self.assertEqual(params[2], '#chan', m,
                        fail_msg='Bad channel name: {got} instead of '
                        '{expects}: {msg}')
                self.assertIn(params[3], {'foo', '@foo', '+foo'}, m,
                        fail_msg='Bad user list after user "foo" joined twice '
                        'the same channel: should contain only user '
                        '"foo" with an optional "+" or "@" prefix, but got: '
                        '{msg}')

    def testListEmpty(self):
        """<https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>
        """
        self.connectClient('foo')
        self.connectClient('bar')
        self.getMessages(1)
        self.sendLine(2, 'LIST')
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='321', # RPL_LISTSTART
                fail_msg='First reply to LIST is not 321 (RPL_LISTSTART), '
                'but: {msg}')
        m = self.getMessage(2)
        self.assertNotEqual(m.command, '322', # RPL_LIST
                'LIST response gives (at least) one channel, whereas there '
                'is none.')
        self.assertMessageEqual(m, command='323', # RPL_LISTEND
                fail_msg='Second reply to LIST is not 322 (RPL_LIST) '
                'or 323 (RPL_LISTEND), or but: {msg}')

    def testListOne(self):
        """When a channel exists, LIST should get it in a reply.
        <https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>
        """
        self.connectClient('foo')
        self.connectClient('bar')
        self.sendLine(1, 'JOIN #chan')
        self.getMessages(1)
        self.sendLine(2, 'LIST')
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='321', # RPL_LISTSTART
                fail_msg='First reply to LIST is not 321 (RPL_LISTSTART), '
                'but: {msg}')
        m = self.getMessage(2)
        self.assertNotEqual(m.command, '323', # RPL_LISTEND
                'LIST response ended (ie. 323, aka RPL_LISTEND) without '
                'listing any channel, whereas there is one.')
        self.assertMessageEqual(m, command='322', # RPL_LIST
                fail_msg='Second reply to LIST is not 322 (RPL_LIST), '
                'nor 323 (RPL_LISTEND) but: {msg}')
        m = self.getMessage(2)
        self.assertNotEqual(m.command, '322', # RPL_LIST
                'LIST response gives (at least) two channels, whereas there '
                'is only one.')
        self.assertMessageEqual(m, command='323', # RPL_LISTEND
                fail_msg='Third reply to LIST is not 322 (RPL_LIST) '
                'or 323 (RPL_LISTEND), or but: {msg}')
