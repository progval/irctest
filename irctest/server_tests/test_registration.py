from irctest import cases
from irctest.irc_utils.message_parser import Message

class RegistrationTestCase(cases.BaseServerTestCase):
    def testRegistration(self):
        self.controller.registerUser(self, 'testuser', 'mypassword')

class SaslTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPlain(self):
        """PLAIN authentication with correct username/password."""
        self.controller.registerUser(self, 'foo', 'sesame')
        self.controller.registerUser(self, 'jilles', 'sesame')
        self.controller.registerUser(self, 'bar', 'sesame')
        self.addClient()
        self.sendLine(1, 'CAP LS 302')
        capabilities = self.getCapLs(1)
        self.assertIn('sasl', capabilities,
                fail_msg='Does not have SASL as the controller claims.')
        if capabilities['sasl'] is not None:
            self.assertIn('PLAIN', capabilities['sasl'])
        self.sendLine(1, 'AUTHENTICATE PLAIN')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='AUTHENTICATE', params=['+'],
                fail_msg='Sent “AUTHENTICATE PLAIN”, server should have '
                'replied with “AUTHENTICATE +”, but instead sent: {msg}')
        self.sendLine(1, 'AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='900',
                fail_msg='Did not send 900 after correct SASL authentication.')
        self.assertEqual(m.params[2], 'jilles', m,
                fail_msg='900 should contain the account name as 3rd argument '
                '({expects}), not {got}: {msg}')
