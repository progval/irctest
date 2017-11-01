"""
<http://ircv3.net/specs/extensions/extended-join-3.1.html>
"""

from irctest import cases
from irctest.irc_utils.message_parser import Message

class MetadataTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    def connectRegisteredClient(self, nick):
        self.addClient()
        self.sendLine(2, 'CAP LS 302')
        capabilities = self.getCapLs(2)
        assert 'sasl' in capabilities
        self.sendLine(2, 'AUTHENTICATE PLAIN')
        m = self.getMessage(2, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='AUTHENTICATE', params=['+'],
                fail_msg='Sent “AUTHENTICATE PLAIN”, server should have '
                'replied with “AUTHENTICATE +”, but instead sent: {msg}')
        self.sendLine(2, 'AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=')
        m = self.getMessage(2, filter_pred=lambda m:m.command != 'NOTICE')
        self.assertMessageEqual(m, command='900',
                fail_msg='Did not send 900 after correct SASL authentication.')
        self.sendLine(2, 'USER f * * :Realname')
        self.sendLine(2, 'NICK {}'.format(nick))
        self.sendLine(2, 'CAP END')
        self.skipToWelcome(2)

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.1')
    def testNotLoggedIn(self):
        self.connectClient('foo', capabilities=['extended-join'],
                skip_if_cap_nak=True)
        self.sendLine(1, 'JOIN #chan')
        self.getMessages(1)
        self.connectClient('bar')
        self.sendLine(2, 'JOIN #chan')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN',
                params=['#chan', '*', 'Realname'],
                fail_msg='Expected “JOIN #chan * :Realname” after '
                'unregistered user joined, got: {msg}')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.1')
    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testNotLoggedIn(self):
        self.connectClient('foo', capabilities=['extended-join'],
                skip_if_cap_nak=True)
        self.joinChannel(1, '#chan')

        self.controller.registerUser(self, 'jilles', 'sesame')
        self.connectRegisteredClient('bar')
        self.joinChannel(2, '#chan')

        m = self.getMessage(1)
        self.assertMessageEqual(m, command='JOIN',
                params=['#chan', 'jilles', 'Realname'],
                fail_msg='Expected “JOIN #chan * :Realname” after '
                'nick “bar” logged in as “jilles” joined, got: {msg}')
