from irctest.cases import ClientTestCase
from irctest.irc_utils.message_parser import Message

class CapTestCase(ClientTestCase):
    def testSendCap(self):
        (hostname, port) = self.server.getsockname()
        self.controller.run(
                hostname=hostname,
                port=port,
                authentication=None,
                )
        self.acceptClient()
        m = self.getMessage()
        self.assertEqual(m.command, 'CAP',
                'First message is not CAP LS.')
        self.assertEqual(m.subcommand, 'LS',
                'First message is not CAP LS.')
        self.assertIn(m.params, ([], ['302'])) # IRCv3.1 or IRVv3.2
