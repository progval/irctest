from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseServerTestCase):
    def testNoReq(self):
        """Test the server handles gracefully clients which do not send
        REQs."""
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP END')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='001')

    def testReqUnavailable(self):
        """Test the server handles gracefully clients which request
        capabilities that are not available"""
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP REQ :foo')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo'])
        self.sendLine(1, 'CAP END')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertEqual(m.command, '001')

    def testNakExactString(self):
        """Make sure the server NAKs with *exactly* the string sent, as
        required by the spec <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-nak-subcommand>"""
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        # Five should be enough to check there is no reordering, even
        # alphabetical
        self.sendLine(1, 'CAP REQ :foo bar baz qux quux')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo bar baz qux quux'])

    def testNakWhole(self):
        """Makes sure the server NAKS all capabilities in a single REQ."""
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.assertIn('multi-prefix', self.getCapLs(1))
        self.sendLine(1, 'CAP REQ :foo multi-prefix bar')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo multi-prefix bar'])
        self.sendLine(1, 'CAP REQ :multi-prefix bar')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['multi-prefix bar'])
        self.sendLine(1, 'CAP REQ :foo multi-prefix')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo multi-prefix'])
        # TODO: make sure multi-prefix is not enabled at this point
        self.sendLine(1, 'CAP REQ :multi-prefix')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='CAP',
                subcommand='ACK', subparams=['multi-prefix'])
