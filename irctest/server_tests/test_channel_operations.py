"""
Section 3.2 of RFC 2812
<https://tools.ietf.org/html/rfc2812#section-3.2>
"""

from irctest import cases
from irctest import client_mock
from irctest import runner
from irctest.irc_utils import ambiguities
from irctest.numerics import RPL_NOTOPIC, RPL_NAMREPLY, RPL_INVITING
from irctest.numerics import ERR_NOSUCHCHANNEL, ERR_NOTONCHANNEL, ERR_CHANOPRIVSNEEDED, ERR_NOSUCHNICK, ERR_INVITEONLYCHAN, ERR_CANNOTSENDTOCHAN, ERR_BADCHANNELKEY, ERR_INVALIDMODEPARAM, ERR_UNKNOWNERROR

MODERN_CAPS = ['server-time', 'message-tags', 'batch', 'labeled-response', 'echo-message', 'account-tag']

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
    def testNormalPart(self):
        self.connectClient('bar')
        self.sendLine(1, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])

        self.connectClient('baz')
        self.sendLine(2, 'JOIN #chan')
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='JOIN', params=['#chan'])

        # skip the rest of the JOIN burst:
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, 'PART #chan :bye everyone')
        # both the PART'ing client and the other channel member should receive a PART line:
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='PART', params=['#chan', 'bye everyone'])
        m = self.getMessage(2)
        self.assertMessageEqual(m, command='PART', params=['#chan', 'bye everyone'])


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

        # clear waiting msgs about cli 2 joining the channel
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
        self.getMessages(1)

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

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testUnsetTopicResponses(self):
        """Test various cases related to RPL_NOTOPIC with set and unset topics."""
        self.connectClient('bar')
        self.sendLine(1, 'JOIN #test')
        messages = self.getMessages(1)
        # shouldn't send RPL_NOTOPIC for a new channel
        self.assertNotIn(RPL_NOTOPIC, [m.command for m in messages])

        self.connectClient('baz')
        self.sendLine(2, 'JOIN #test')
        messages = self.getMessages(2)
        # topic is still unset, shouldn't send RPL_NOTOPIC on initial join
        self.assertNotIn(RPL_NOTOPIC, [m.command for m in messages])

        self.sendLine(2, 'TOPIC #test')
        messages = self.getMessages(2)
        # explicit TOPIC should receive RPL_NOTOPIC
        self.assertIn(RPL_NOTOPIC, [m.command for m in messages])

        self.sendLine(1, 'TOPIC #test :new topic')
        self.getMessages(1)
        # client 2 should get the new TOPIC line
        messages = [message for message in self.getMessages(2) if message.command == 'TOPIC']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].params, ['#test', 'new topic'])

        # unset the topic:
        self.sendLine(1, 'TOPIC #test :')
        self.getMessages(1)
        self.connectClient('qux')
        self.sendLine(3, 'join #test')
        messages = self.getMessages(3)
        # topic is once again unset, shouldn't send RPL_NOTOPIC on initial join
        self.assertNotIn(RPL_NOTOPIC, [m.command for m in messages])

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
        if m.command == '321':
            # skip RPL_LISTSTART
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
        if m.command == '321':
            # skip RPL_LISTSTART
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
    def testKickPrivileges(self):
        """Test who has the ability to kick / what error codes are sent for invalid kicks."""
        self.connectClient('foo')
        self.sendLine(1, 'JOIN #chan')
        self.getMessages(1)

        self.connectClient('bar')
        self.sendLine(2, 'JOIN #chan')

        messages = self.getMessages(2)
        names = set()
        for message in messages:
            if message.command == RPL_NAMREPLY:
                names.update(set(message.params[-1].split()))
        # assert foo is opped
        self.assertIn('@foo', names, f'unexpected names: {names}')

        self.connectClient('baz')

        self.sendLine(3, 'KICK #chan bar')
        replies = set(m.command for m in self.getMessages(3))
        self.assertTrue(
            ERR_NOTONCHANNEL in replies or ERR_CHANOPRIVSNEEDED in replies or ERR_NOSUCHCHANNEL in replies,
            f'did not receive acceptable error code for kick from outside channel: {replies}')

        self.joinChannel(3, '#chan')
        self.getMessages(3)
        self.sendLine(3, 'KICK #chan bar')
        replies = set(m.command for m in self.getMessages(3))
        # now we're a channel member so we should receive ERR_CHANOPRIVSNEEDED
        self.assertIn(ERR_CHANOPRIVSNEEDED, replies)

        self.sendLine(1, 'MODE #chan +o baz')
        self.getMessages(1)
        # should be able to kick an unprivileged user:
        self.sendLine(3, 'KICK #chan bar')
        # should be able to kick an operator:
        self.sendLine(3, 'KICK #chan foo')
        baz_replies = set(m.command for m in self.getMessages(3))
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, baz_replies)
        kick_targets = [m.params[1] for m in self.getMessages(1) if m.command == 'KICK']
        # foo should see bar and foo being kicked
        self.assertTrue(any(target.startswith('foo') for target in kick_targets), f'unexpected kick targets: {kick_targets}')
        self.assertTrue(any(target.startswith('bar') for target in kick_targets), f'unexpected kick targets: {kick_targets}')

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

        mgroup = self.getMessages(4)
        self.assertGreaterEqual(len(mgroup), 2)
        m1, m2 = mgroup[:2]

        for m in m1, m2:
            self.assertEqual(m.command, 'KICK')

            self.assertEqual(len(m.params), 3)
            self.assertEqual(m.params[0], '#chan')
            self.assertEqual(m.params[2], 'bye')
        
        if (m1.params[1] == 'bar' and m2.params[1] == 'baz') or (m1.params[1] == 'baz' and m2.params[1] == 'bar'):
            ...  # success
        else:
            raise AssertionError('Middle params [{}, {}] are not correct.'.format(m1.params[1], m2.params[1]))

    @cases.SpecificationSelector.requiredBySpecification('RFC-deprecated')
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

    @cases.SpecificationSelector.requiredBySpecification('RFC-deprecated')
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


class InviteTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testInvites(self):
        """Test some basic functionality related to INVITE and the +i mode."""
        self.connectClient('foo')
        self.joinChannel(1, '#chan')
        self.sendLine(1, 'MODE #chan +i')
        self.getMessages(1)
        self.sendLine(1, 'INVITE bar #chan')
        m = self.getMessage(1)
        self.assertEqual(m.command, ERR_NOSUCHNICK)

        self.connectClient('bar')
        self.sendLine(2, 'JOIN #chan')
        m = self.getMessage(2)
        self.assertEqual(m.command, ERR_INVITEONLYCHAN)

        self.sendLine(1, 'INVITE bar #chan')
        m = self.getMessage(1)
        self.assertEqual(m.command, RPL_INVITING)
        # modern/ircv3 param order: inviter, invitee, channel
        self.assertEqual(m.params, ['foo', 'bar', '#chan'])
        m = self.getMessage(2)
        self.assertEqual(m.command, 'INVITE')
        self.assertTrue(m.prefix.startswith("foo")) # nickmask of inviter
        self.assertEqual(m.params, ['bar', '#chan'])

        # we were invited, so join should succeed now
        self.joinChannel(2, '#chan')


class ChannelQuitTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testQuit(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes [...] QUIT”
        <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient('bar')
        self.joinChannel(1, '#chan')
        self.connectClient('qux')
        self.sendLine(2, 'JOIN #chan')
        self.getMessages(2)

        self.getMessages(1)
        self.sendLine(2, 'QUIT :qux out')
        self.getMessages(2)
        m = self.getMessage(1)
        self.assertEqual(m.command, 'QUIT')
        self.assertTrue(m.prefix.startswith('qux')) # nickmask of quitter
        self.assertIn('qux out', m.params[0])


class NoCTCPTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testQuit(self):
        self.connectClient('bar')
        self.joinChannel(1, '#chan')
        self.sendLine(1, 'MODE #chan +C')
        self.getMessages(1)

        self.connectClient('qux')
        self.joinChannel(2, '#chan')
        self.getMessages(2)

        self.sendLine(1, 'PRIVMSG #chan :\x01ACTION hi\x01')
        self.getMessages(1)
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='PRIVMSG', params=['#chan', '\x01ACTION hi\x01'])

        self.sendLine(1, 'PRIVMSG #chan :\x01PING 1473523796 918320\x01')
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command=ERR_CANNOTSENDTOCHAN)
        ms = self.getMessages(2)
        self.assertEqual(ms, [])

class KeyTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testKeyNormal(self):
        self.connectClient('bar')
        self.joinChannel(1, '#chan')
        self.sendLine(1, 'MODE #chan +k beer')
        self.getMessages(1)

        self.connectClient('qux')
        self.getMessages(2)
        self.sendLine(2, 'JOIN #chan')
        reply = self.getMessages(2)
        self.assertNotIn('JOIN', {msg.command for msg in reply})
        self.assertIn(ERR_BADCHANNELKEY, {msg.command for msg in reply})

        self.sendLine(2, 'JOIN #chan beer')
        reply = self.getMessages(2)
        self.assertMessageEqual(reply[0], command='JOIN', params=['#chan'])

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testKeyValidation(self):
        # oragono issue #1021
        self.connectClient('bar')
        self.joinChannel(1, '#chan')
        self.sendLine(1, 'MODE #chan +k :invalid channel passphrase')
        reply = self.getMessages(1)
        self.assertNotIn(ERR_UNKNOWNERROR, {msg.command for msg in reply})
        self.assertIn(ERR_INVALIDMODEPARAM, {msg.command for msg in reply})


class AuditoriumTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testAuditorium(self):
        self.connectClient('bar', name='bar', capabilities=MODERN_CAPS)
        self.joinChannel('bar', '#auditorium')
        self.getMessages('bar')
        self.sendLine('bar', 'MODE #auditorium +u')
        modelines = [msg for msg in self.getMessages('bar') if msg.command == 'MODE']
        self.assertEqual(len(modelines), 1)
        self.assertMessageEqual(modelines[0], params=['#auditorium', '+u'])

        self.connectClient('guest1', name='guest1', capabilities=MODERN_CAPS)
        self.joinChannel('guest1', '#auditorium')
        self.getMessages('guest1')
        # chanop should get a JOIN message
        join_msgs = [msg for msg in self.getMessages('bar') if msg.command == 'JOIN']
        self.assertEqual(len(join_msgs), 1)
        self.assertMessageEqual(join_msgs[0], nick='guest1', params=['#auditorium'])

        self.connectClient('guest2', name='guest2', capabilities=MODERN_CAPS)
        self.joinChannel('guest2', '#auditorium')
        self.getMessages('guest2')
        # chanop should get a JOIN message
        join_msgs = [msg for msg in self.getMessages('bar') if msg.command == 'JOIN']
        self.assertEqual(len(join_msgs), 1)
        self.assertMessageEqual(join_msgs[0], nick='guest2', params=['#auditorium'])
        # fellow unvoiced participant should not
        unvoiced_join_msgs = [msg for msg in self.getMessages('guest1') if msg.command == 'JOIN']
        self.assertEqual(len(unvoiced_join_msgs), 0)

        self.connectClient('guest3', name='guest3', capabilities=MODERN_CAPS)
        self.joinChannel('guest3', '#auditorium')
        self.getMessages('guest3')

        self.sendLine('bar', 'PRIVMSG #auditorium hi')
        echo_message = [msg for msg in self.getMessages('bar') if msg.command == 'PRIVMSG'][0]
        self.assertEqual(echo_message, self.getMessages('guest1')[0])
        self.assertEqual(echo_message, self.getMessages('guest2')[0])
        self.assertEqual(echo_message, self.getMessages('guest3')[0])

        # unvoiced users can speak
        self.sendLine('guest1', 'PRIVMSG #auditorium :hi you')
        echo_message = [msg for msg in self.getMessages('guest1') if msg.command == 'PRIVMSG'][0]
        self.assertEqual(self.getMessages('bar'), [echo_message])
        self.assertEqual(self.getMessages('guest2'), [echo_message])
        self.assertEqual(self.getMessages('guest3'), [echo_message])

        def names(client):
            self.sendLine(client, 'NAMES #auditorium')
            result = set()
            for msg in self.getMessages(client):
                if msg.command == RPL_NAMREPLY:
                    result.update(msg.params[-1].split())
            return result

        self.assertEqual(names('bar'), {'@bar', 'guest1', 'guest2', 'guest3'})
        self.assertEqual(names('guest1'), {'@bar',})
        self.assertEqual(names('guest2'), {'@bar',})
        self.assertEqual(names('guest3'), {'@bar',})

        self.sendLine('bar', 'MODE #auditorium +v guest1')
        modeLine = [msg for msg in self.getMessages('bar') if msg.command == 'MODE'][0]
        self.assertEqual(self.getMessages('guest1'), [modeLine])
        self.assertEqual(self.getMessages('guest2'), [modeLine])
        self.assertEqual(self.getMessages('guest3'), [modeLine])
        self.assertEqual(names('bar'), {'@bar', '+guest1', 'guest2', 'guest3'})
        self.assertEqual(names('guest2'), {'@bar', '+guest1'})
        self.assertEqual(names('guest3'), {'@bar', '+guest1'})

        self.sendLine('guest1', 'PART #auditorium')
        part = [msg for msg in self.getMessages('guest1') if msg.command == 'PART'][0]
        # everyone should see voiced PART
        self.assertEqual(self.getMessages('bar')[0], part)
        self.assertEqual(self.getMessages('guest2')[0], part)
        self.assertEqual(self.getMessages('guest3')[0], part)

        self.joinChannel('guest1', '#auditorium')
        self.getMessages('guest1')
        self.getMessages('bar')

        self.sendLine('guest2', 'PART #auditorium')
        part = [msg for msg in self.getMessages('guest2') if msg.command == 'PART'][0]
        self.assertEqual(self.getMessages('bar'), [part])
        # part should be hidden from unvoiced participants
        self.assertEqual(self.getMessages('guest1'), [])
        self.assertEqual(self.getMessages('guest3'), [])

        self.sendLine('guest3', 'QUIT')
        self.assertDisconnected('guest3')
        # quit should be hidden from unvoiced participants
        self.assertEqual(len([msg for msg in self.getMessages('bar') if msg.command =='QUIT']), 1)
        self.assertEqual(len([msg for msg in self.getMessages('guest1') if msg.command =='QUIT']), 0)


class TopicPrivileges(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testTopicPrivileges(self):
        # test the +t channel mode, which prevents unprivileged users from changing the topic
        self.connectClient('bar', name='bar')
        self.joinChannel('bar', '#chan')
        self.getMessages('bar')
        self.sendLine('bar', 'MODE #chan +t')
        replies = {msg.command for msg in self.getMessages('bar')}
        # success response is undefined, may be MODE or may be 324 RPL_CHANNELMODEIS,
        # depending on whether this was a no-op
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)
        self.sendLine('bar', 'TOPIC #chan :new topic')
        replies = {msg.command for msg in self.getMessages('bar')}
        self.assertIn('TOPIC', replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient('qux', name='qux')
        self.joinChannel('qux', '#chan')
        self.getMessages('qux')
        self.sendLine('qux', 'TOPIC #chan :new topic')
        replies = {msg.command for msg in self.getMessages('qux')}
        self.assertIn(ERR_CHANOPRIVSNEEDED, replies)
        self.assertNotIn('TOPIC', replies)

        self.sendLine('bar', 'MODE #chan +v qux')
        replies = {msg.command for msg in self.getMessages('bar')}
        self.assertIn('MODE', replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # regression test: +v cannot change the topic of a +t channel
        self.sendLine('qux', 'TOPIC #chan :new topic')
        replies = {msg.command for msg in self.getMessages('qux')}
        self.assertIn(ERR_CHANOPRIVSNEEDED, replies)
        self.assertNotIn('TOPIC', replies)


class OpModerated(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testOpModerated(self):
        # test the +U channel mode
        self.connectClient('chanop', name='chanop', capabilities=MODERN_CAPS)
        self.joinChannel('chanop', '#chan')
        self.getMessages('chanop')
        self.sendLine('chanop', 'MODE #chan +U')
        replies = {msg.command for msg in self.getMessages('chanop')}
        self.assertIn('MODE', replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient('baz', name='baz', capabilities=MODERN_CAPS)
        self.joinChannel('baz', '#chan')
        self.sendLine('baz', 'PRIVMSG #chan :hi from baz')
        echo = self.getMessages('baz')[0]
        self.assertMessageEqual(echo, command='PRIVMSG', params=['#chan', 'hi from baz'])
        self.assertEqual([msg for msg in self.getMessages('chanop') if msg.command == 'PRIVMSG'], [echo])

        self.connectClient('qux', name='qux', capabilities=MODERN_CAPS)
        self.joinChannel('qux', '#chan')
        self.sendLine('qux', 'PRIVMSG #chan :hi from qux')
        echo = self.getMessages('qux')[0]
        self.assertMessageEqual(echo, command='PRIVMSG', params=['#chan', 'hi from qux'])
        # message is relayed to chanop but not to unprivileged
        self.assertEqual([msg for msg in self.getMessages('chanop') if msg.command == 'PRIVMSG'], [echo])
        self.assertEqual([msg for msg in self.getMessages('baz') if msg.command == 'PRIVMSG'], [])

        self.sendLine('chanop', 'MODE #chan +v qux')
        self.getMessages('chanop')
        self.sendLine('qux', 'PRIVMSG #chan :hi again from qux')
        echo = [msg for msg in self.getMessages('qux') if msg.command == 'PRIVMSG'][0]
        self.assertMessageEqual(echo, command='PRIVMSG', params=['#chan', 'hi again from qux'])
        self.assertEqual([msg for msg in self.getMessages('chanop') if msg.command == 'PRIVMSG'], [echo])
        self.assertEqual([msg for msg in self.getMessages('baz') if msg.command == 'PRIVMSG'], [echo])
