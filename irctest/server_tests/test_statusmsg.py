from irctest import cases
from irctest.numerics import RPL_NAMREPLY

class StatusmsgTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testInIsupport(self):
        """Check that the expected STATUSMSG parameter appears in our isupport list."""
        isupport = self.getISupport()
        self.assertEqual(isupport['STATUSMSG'], '~&@%+')

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testStatusmsg(self):
        """Test that STATUSMSG are sent to the intended recipients, with the intended prefixes."""
        self.connectClient('chanop')
        self.joinChannel(1, '#chan')
        self.getMessages(1)
        self.connectClient('joe')
        self.joinChannel(2, '#chan')
        self.getMessages(2)

        self.connectClient('schmoe')
        self.sendLine(3, 'join #chan')
        messages = self.getMessages(3)
        names = set()
        for message in messages:
            if message.command == RPL_NAMREPLY:
                names.update(set(message.params[-1].split()))
        # chanop should be opped
        self.assertEqual(names, {'@chanop', 'joe', 'schmoe'}, f'unexpected names: {names}')

        self.sendLine(3, 'privmsg @#chan :this message is for operators')
        self.getMessages(3)

        # check the operator's messages
        statusMsg = self.getMessage(1, filter_pred=lambda m:m.command == 'PRIVMSG')
        self.assertMessageEqual(statusMsg, params=['@#chan', 'this message is for operators'])

        # check the non-operator's messages
        unprivilegedMessages = [msg for msg in self.getMessages(2) if msg.command == 'PRIVMSG']
        self.assertEqual(len(unprivilegedMessages), 0)
