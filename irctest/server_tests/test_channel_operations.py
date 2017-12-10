"""
Section 3.2 of RFC 2812
<https://tools.ietf.org/html/rfc2812#section-3.2>
"""

from irctest import cases
from irctest import client_mock
from irctest import runner
from irctest.irc_utils import ambiguities
from irctest.irc_utils.message_parser import Message

class JoinTestCase(cases.BaseServerTestCase):
    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812',
            strict=True)
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

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
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
                        fail_msg='Bad channel prefix: {item} not in {list}: {msg}')
                self.assertEqual(params[2], '#chan', m,
                        fail_msg='Bad channel name: {got} instead of '
                        '{expects}: {msg}')
                self.assertIn(params[3], {'foo', '@foo', '+foo'}, m,
                        fail_msg='Bad user list: should contain only user '
                        '"foo" with an optional "+" or "@" prefix, but got: '
                        '{msg}')


    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
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

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
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
                        fail_msg='Bad channel prefix: {item} not in {list}: {msg}')
                self.assertEqual(params[2], '#chan', m,
                        fail_msg='Bad channel name: {got} instead of '
                        '{expects}: {msg}')
                self.assertIn(params[3], {'foo', '@foo', '+foo'}, m,
                        fail_msg='Bad user list after user "foo" joined twice '
                        'the same channel: should contain only user '
                        '"foo" with an optional "+" or "@" prefix, but got: '
                        '{msg}')

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testTopic(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes […] TOPIC”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient('foo')
        self.joinChannel(1, '#chan')

        self.connectClient('bar')
        self.joinChannel(2, '#chan')

        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(1)
        self.getMessages(2)

        # TODO: check foo is opped OR +t is unset

        self.sendLine(1, 'TOPIC #chan :T0P1C')
        try:
            m = self.getMessage(1)
            if m.command == '482':
                raise runner.ImplementationChoice(
                        'Channel creators are not opped by default, and '
                        'channel modes to no allow regular users to change '
                        'topic.')
            self.assertMessageEqual(m, command='TOPIC')
        except client_mock.NoMessageException:
            # The RFCs do not say TOPIC must be echoed
            pass
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='TOPIC', params=['#chan', 'T0P1C'])

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testTopicMode(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes […] TOPIC”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient('foo')
        self.joinChannel(1, '#chan')

        self.connectClient('bar')
        self.joinChannel(2, '#chan')

        self.getMessages(1)
        self.getMessages(2)

        # TODO: check foo is opped

        self.sendLine(1, 'MODE #chan +t')
        try:
            m = self.getMessage(1)
            if m.command == '482':
                raise runner.ImplementationChoice(
                        'Channel creators are not opped by default.')
            self.assertMessageEqual(m, command='TOPIC')
        except client_mock.NoMessageException:
            # The RFCs do not say TOPIC must be echoed
            pass
        self.sendLine(2, 'TOPIC #chan :T0P1C')
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='482',
                fail_msg='Non-op user was not refused use of TOPIC: {msg}')
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(1, 'MODE #chan -t')
        self.getMessages(1)
        self.sendLine(2, 'TOPIC #chan :T0P1C')
        try:
            m = self.getMessage(2)
            self.assertNotEqual(m.command, '482',
                    msg='User was refused TOPIC whereas +t was not '
                    'set: {}'.format(m))
        except client_mock.NoMessageException:
            # The RFCs do not say TOPIC must be echoed
            pass
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='TOPIC', params=['#chan', 'T0P1C'])

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testTopicNonexistentChannel(self):
        """RFC2812 specifies ERR_NOTONCHANNEL as the correct response to TOPIC
        on a nonexistent channel. The modern spec prefers ERR_NOSUCHCHANNEL.

        <https://tools.ietf.org/html/rfc2812#section-3.2.4>
        <http://modern.ircdocs.horse/#topic-message>
        """
        self.connectClient('foo')
        self.sendLine(1, 'TOPIC #chan')
        m = self.getMessage(1)
        # either 403 ERR_NOSUCHCHANNEL or 443 ERR_NOTONCHANNEL
        self.assertIn(m.command, ('403', '443'))

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
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

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
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
                fail_msg='LIST response ended (ie. 323, aka RPL_LISTEND) '
                'without listing any channel, whereas there is one.')
        self.assertMessageEqual(m, command='322', # RPL_LIST
                fail_msg='Second reply to LIST is not 322 (RPL_LIST), '
                'nor 323 (RPL_LISTEND) but: {msg}')
        m = self.getMessage(2)
        self.assertNotEqual(m.command, '322', # RPL_LIST
                fail_msg='LIST response gives (at least) two channels, '
                'whereas there is only one.')
        self.assertMessageEqual(m, command='323', # RPL_LISTEND
                fail_msg='Third reply to LIST is not 322 (RPL_LIST) '
                'or 323 (RPL_LISTEND), or but: {msg}')

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testKickSendsMessages(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes […] KICK”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient('foo')
        self.joinChannel(1, '#chan')

        self.connectClient('bar')
        self.joinChannel(2, '#chan')

        self.connectClient('baz')
        self.joinChannel(3, '#chan')

        # TODO: check foo is an operator

        import time
        time.sleep(0.1)
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)
        self.sendLine(1, 'KICK #chan bar :bye')
        try:
            m = self.getMessage(1)
            if m.command == '482':
                raise runner.ImplementationChoice(
                        'Channel creators are not opped by default.')
            self.assertMessageEqual(m, command='KICK')
        except client_mock.NoMessageException:
            # The RFCs do not say KICK must be echoed
            pass
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='KICK',
                params=['#chan', 'bar', 'bye'])
        m = self.getMessage(3)
        self.assertMessageEqual(m, command='KICK',
                params=['#chan', 'bar', 'bye'])

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testKickNonexistentChannel(self):
        """“Kick command [...] Numeric replies: [...] ERR_NOSUCHCHANNEL."""
        self.connectClient('foo')
        self.sendLine(1, 'KICK #chan nick')
        m = self.getMessage(1)
        # should return ERR_NOSUCHCHANNEL
        self.assertMessageEqual(m, command='403')

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testDoubleKickMessages(self):
        """“The server MUST NOT send KICK messages with multiple channels or
        users to clients.  This is necessarily to maintain backward
        compatibility with old client software.”
        -- https://tools.ietf.org/html/rfc2812#section-3.2.8
        """
        self.connectClient('foo')
        self.joinChannel(1, '#chan')

        self.connectClient('bar')
        self.joinChannel(2, '#chan')

        self.connectClient('baz')
        self.joinChannel(3, '#chan')

        self.connectClient('qux')
        self.joinChannel(4, '#chan')

        # TODO: check foo is an operator

        # Synchronize
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)
        self.getMessages(4)

        self.sendLine(1, 'KICK #chan,#chan bar,baz :bye')
        try:
            m = self.getMessage(1)
            if m.command == '482':
                raise runner.OptionalExtensionNotSupported(
                        'Channel creators are not opped by default.')
            if m.command in {'401', '403'}:
                raise runner.NotImplementedByController(
                        'Multi-target KICK')
        except client_mock.NoMessageException:
            # The RFCs do not say KICK must be echoed
            pass

        # TODO: could be in the other order
        m = self.getMessage(4)
        self.assertMessageEqual(m, command='KICK',
                params=['#chan', 'bar', 'bye'])
        m = self.getMessage(4)
        self.assertMessageEqual(m, command='KICK',
                params=['#chan', 'baz', 'bye'])

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testInviteNonExistingChannelTransmitted(self):
        """“There is no requirement that the channel the target user is being
        invited to must exist or be a valid channel.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.7>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.7>

        “Only the user inviting and the user being invited will receive
        notification of the invitation.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.7>
        """
        self.connectClient('foo')
        self.connectClient('bar')
        self.getMessages(1)
        self.getMessages(2)
        self.sendLine(1, 'INVITE #chan bar')
        self.getMessages(1)
        l = self.getMessages(2)
        self.assertNotEqual(l, [],
                fail_msg='After using “INVITE #chan bar” while #chan does '
                'not exist, “bar” received nothing.')
        self.assertMessageEqual(l[0], command='INVITE',
                params=['#chan', 'bar'],
                fail_msg='After “foo” invited “bar” do non-existing channel '
                '#chan, “bar” should have received “INVITE #chan bar” but '
                'got this instead: {msg}')

    @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812')
    def testInviteNonExistingChannelEchoed(self):
        """“There is no requirement that the channel the target user is being
        invited to must exist or be a valid channel.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.7>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.7>

        “Only the user inviting and the user being invited will receive
        notification of the invitation.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.7>
        """
        self.connectClient('foo')
        self.connectClient('bar')
        self.getMessages(1)
        self.getMessages(2)
        self.sendLine(1, 'INVITE #chan bar')
        l = self.getMessages(1)
        self.assertNotEqual(l, [],
                fail_msg='After using “INVITE #chan bar” while #chan does '
                'not exist, the author received nothing.')
        self.assertMessageEqual(l[0], command='INVITE',
                params=['#chan', 'bar'],
                fail_msg='After “foo” invited “bar” do non-existing channel '
                '#chan, “foo” should have received “INVITE #chan bar” but '
                'got this instead: {msg}')

class testChannelCaseSensitivity(cases.BaseServerTestCase):
    def _testChannelsEquivalent(casemapping, name1, name2):
        @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812',
                strict=True)
        def f(self):
            self.connectClient('foo')
            self.connectClient('bar')
            if self.server_support['CASEMAPPING'] != casemapping:
                raise runner.NotImplementedByController('Casemapping {} not implemented'.format(casemapping))
            self.joinClient(1, name1)
            self.joinClient(2, name2)
            try:
                m = self.getMessage(1)
                self.assertMessageEqual(m, command='JOIN',
                        nick='bar')
            except client_mock.NoMessageException:
                raise AssertionError(
                        'Channel names {} and {} are not equivalent.'
                        .format(name1, name2))
        f.__name__ = 'testEquivalence__{}__{}'.format(name1, name2)
        return f
    def _testChannelsNotEquivalent(casemapping, name1, name2):
        @cases.SpecificationSelector.requiredBySpecification('RFC1459', 'RFC2812',
                strict=True)
        def f(self):
            self.connectClient('foo')
            self.connectClient('bar')
            if self.server_support['CASEMAPPING'] != casemapping:
                raise runner.NotImplementedByController('Casemapping {} not implemented'.format(casemapping))
            self.joinClient(1, name1)
            self.joinClient(2, name2)
            try:
                m = self.getMessage(1)
            except client_mock.NoMessageException:
                pass
            else:
                self.assertMessageEqual(m, command='JOIN',
                        nick='bar') # This should always be true
                raise AssertionError(
                        'Channel names {} and {} are equivalent.'
                        .format(name1, name2))
        f.__name__ = 'testEquivalence__{}__{}'.format(name1, name2)
        return f

    testAsciiSimpleEquivalent = _testChannelsEquivalent('ascii', '#Foo', '#foo')
    testAsciiSimpleNotEquivalent = _testChannelsNotEquivalent('ascii', '#Foo', '#fooa')

    testRfcSimpleEquivalent = _testChannelsEquivalent('rfc1459', '#Foo', '#foo')
    testRfcSimpleNotEquivalent = _testChannelsNotEquivalent('rfc1459', '#Foo', '#fooa')
    testRfcFancyEquivalent = _testChannelsEquivalent('rfc1459', '#F]|oo{', '#f}\\oo[')
    testRfcFancyNotEquivalent = _testChannelsEquivalent('rfc1459', '#F}o\\o[', '#f]o|o{')
