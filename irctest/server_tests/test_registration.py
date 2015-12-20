from irctest import cases
from irctest.irc_utils.message_parser import Message

class RegistrationTestCase(cases.BaseServerTestCase):
    def testRegistration(self):
        self.controller.registerUser(self, 'testuser')
