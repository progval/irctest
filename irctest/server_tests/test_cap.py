from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseServerTestCase):
    def testNoCap(self):
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        while True: # Ignore boring connection messages
            m = self.getMessage(1)
            if m.command != 'NOTICE':
                break
        print(m)
