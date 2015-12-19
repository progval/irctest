from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseServerTestCase):
    def testNoReq(self):
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertEqual(m.command, 'CAP')
        self.assertEqual(len(m.params), 3, m)
        self.assertEqual(m.params[0:2], ['*', 'LS'], m)
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP END')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertEqual(m.command, '001')
