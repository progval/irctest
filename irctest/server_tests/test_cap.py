from irctest import cases
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseServerTestCase):
    def testNoReq(self):
        """Test the server handles gracefully clients which do not send
        REQs.

        “Clients that support capabilities but do not wish to enter
        negotiation SHOULD send CAP END upon connection to the server.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-end-subcommand>
        """
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP END')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='001')

    def testReqUnavailable(self):
        """Test the server handles gracefully clients which request
        capabilities that are not available.
        <http://ircv3.net/specs/core/capability-negotiation-3.1.html>
        """
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP REQ :foo')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo'])
        self.sendLine(1, 'CAP END')
        m = self.getRegistrationMessage(1)
        self.assertEqual(m.command, '001')

    def testNakExactString(self):
        """“The argument of the NAK subcommand MUST consist of at least the
        first 100 characters of the capability list in the REQ subcommand which
        triggered the NAK.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-nak-subcommand>
        """
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        # Five should be enough to check there is no reordering, even
        # alphabetical
        self.sendLine(1, 'CAP REQ :foo bar baz qux quux')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo bar baz qux quux'])

    def testNakWhole(self):
        """“The capability identifier set must be accepted as a whole, or
        rejected entirely.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-req-subcommand>
        """
        self.addClient(1)
        self.sendLine(1, 'CAP LS 302')
        self.assertIn('multi-prefix', self.getCapLs(1))
        self.sendLine(1, 'CAP REQ :foo multi-prefix bar')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo multi-prefix bar'])
        self.sendLine(1, 'CAP REQ :multi-prefix bar')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['multi-prefix bar'])
        self.sendLine(1, 'CAP REQ :foo multi-prefix')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='CAP',
                subcommand='NAK', subparams=['foo multi-prefix'])
        # TODO: make sure multi-prefix is not enabled at this point
        self.sendLine(1, 'CAP REQ :multi-prefix')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='CAP',
                subcommand='ACK', subparams=['multi-prefix'])
