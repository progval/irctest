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
        self.assertIn('sasl', capabilities)
        if capabilities['sasl'] is not None:
            self.assertIn('PLAIN', capabilities['sasl'])
        self.sendLine(1, 'AUTHENTICATE PLAIN')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='AUTHENTICATE', params=['+'])
        self.sendLine(1, 'AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=')
        m = self.getMessage(1, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='900')
        self.assertEqual(m.params[2], 'jilles', m)
