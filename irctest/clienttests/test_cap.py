from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseClientTestCase, cases.ClientNegociationHelper):
    def testSendCap(self):
        self.readCapLs()

    def testEmptyCapLs(self):
        self.readCapLs()
        self.sendLine('CAP * LS :')
        m = self.getMessage(filter_pred=self.userNickPredicate)
        self.assertEqual(m, Message([], None, 'CAP', ['END']))
