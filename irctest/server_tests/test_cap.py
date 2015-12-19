from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseServerTestCase):
    def testNoReq(self):
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP', target='*',
                subcommand='LS')
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP END')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='001')

    def testReqUnavailable(self):
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP')
        self.assertMessageEqual(m, command='CAP', target='*',
                subcommand='LS')
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP REQ :invalid-capability')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['invalid-capability'])
        self.sendLine(1, 'CAP END')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertEqual(m.command, '001')

    def testNakExactString(self):
        """Make sure the server NAKs with *exactly* the string sent, as
        required by the spec <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-nak-subcommand>"""
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP')
        self.assertMessageEqual(m, command='CAP', target='*',
                subcommand='LS')
        # Five should be enough to check there is no reordering, even
        # alphabetical
        self.sendLine(1, 'CAP REQ :foo bar baz qux quux')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo bar baz qux quux'])
