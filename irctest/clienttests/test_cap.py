from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseClientTestCase, cases.NegociationHelper):
    def testSendCap(self):
        self.readCapLs()
