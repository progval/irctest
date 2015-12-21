from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseClientTestCase, cases.ClientNegociationHelper):
    def testSendCap(self):
        """Send CAP LS 302 and read the result."""
        self.readCapLs()

    def testEmptyCapLs(self):
        """Empty result to CAP LS. Client should send CAP END."""
        m = self.negotiateCapabilities([])
        self.assertEqual(m, Message([], None, 'CAP', ['END']))
