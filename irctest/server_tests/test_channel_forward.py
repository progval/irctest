from irctest import cases
from irctest.numerics import ERR_CHANOPRIVSNEEDED, ERR_INVALIDMODEPARAM, ERR_LINKCHANNEL

MODERN_CAPS = ['server-time', 'message-tags', 'batch', 'labeled-response', 'echo-message', 'account-tag']

class ChannelForwarding(cases.BaseServerTestCase):
    """Test the +f channel forwarding mode."""

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testChannelForwarding(self):
        self.connectClient('bar', name='bar', capabilities=MODERN_CAPS)
        self.connectClient('baz', name='baz', capabilities=MODERN_CAPS)
        self.joinChannel('bar', '#bar')
        self.joinChannel('bar', '#bar_two')
        self.joinChannel('baz', '#baz')

        self.sendLine('bar', 'MODE #bar +f #nonexistent')
        msg = self.getMessage('bar')
        self.assertMessageEqual(msg, command=ERR_INVALIDMODEPARAM)

        # need chanops in the target channel as well
        self.sendLine('bar', 'MODE #bar +f #baz')
        responses = set(msg.command for msg in self.getMessages('bar'))
        self.assertIn(ERR_CHANOPRIVSNEEDED, responses)

        self.sendLine('bar', 'MODE #bar +f #bar_two')
        msg = self.getMessage('bar')
        self.assertMessageEqual(msg, command='MODE', params=['#bar', '+f', '#bar_two'])

        # can still join the channel fine
        self.joinChannel('baz', '#bar')
        self.sendLine('baz', 'PART #bar')
        self.getMessages('baz')

        # now make it invite-only, which should cause forwarding
        self.sendLine('bar', 'MODE #bar +i')
        self.getMessages('bar')

        self.sendLine('baz', 'JOIN #bar')
        msgs = self.getMessages('baz')
        forward = [msg for msg in msgs if msg.command == ERR_LINKCHANNEL]
        self.assertEqual(forward[0].params[:3], ['baz', '#bar', '#bar_two'])
        join = [msg for msg in msgs if msg.command == 'JOIN']
        self.assertMessageEqual(join[0], params=['#bar_two'])
