from irctest import cases
from irctest.numerics import RPL_ISUPPORT

class StatusmsgTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testInIsupport(self):
        """Check that the expected STATUSMSG parameter appears in our isupport list."""
        self.addClient()
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK bar')
        self.skipToWelcome(1)
        messages = self.getMessages(1)
        isupport = set()
        for message in messages:
            if message.command == RPL_ISUPPORT:
                isupport.update(message.params)
        self.assertIn('STATUSMSG=~&@%+', isupport)
