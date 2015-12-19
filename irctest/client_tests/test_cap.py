from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseClientTestCase, cases.ClientNegociationHelper):
    def testSendCap(self):
        self.readCapLs()

    def testEmptyCapLs(self):
        m = self.negotiateCapabilities([])
        self.assertEqual(m, Message([], None, 'CAP', ['END']))
