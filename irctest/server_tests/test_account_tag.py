"""
<http://ircv3.net/specs/extensions/account-tag-3.2.html>
"""

from irctest import cases
from irctest.client_mock import NoMessageException
from irctest.basecontrollers import NotImplementedByController

class AccountTagTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
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

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPrivmsg(self):
        self.connectClient('foo', capabilities=['account-tag'],
                skip_if_cap_nak=True)
        self.getMessages(1)
        self.controller.registerUser(self, 'jilles', 'sesame')
        self.connectRegisteredClient('bar')
        self.sendLine(2, 'PRIVMSG foo :hi')
        self.getMessages(2)
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='PRIVMSG', # RPL_MONONLINE
                fail_msg='Sent non-730 (RPL_MONONLINE) message after '
                '“bar” sent a PRIVMSG: {msg}')
        self.assertIn('account', m.tags, m,
                fail_msg='PRIVMSG by logged in nick '
                'does not contain an account tag: {msg}')
        self.assertEqual(m.tags['account'], 'jilles', m,
                fail_msg='PRIVMSG by logged in nick '
                'does not contain the correct account tag (should be '
                '“jilles”): {msg}')


    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testMonitor(self):
        self.connectClient('foo', capabilities=['account-tag'],
                skip_if_cap_nak=True)
        if 'MONITOR' not in self.server_support:
            raise NotImplementedByController('MONITOR')
        self.sendLine(1, 'MONITOR + bar')
        self.getMessages(1)
        self.controller.registerUser(self, 'jilles', 'sesame')
        self.connectRegisteredClient('bar')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='730', # RPL_MONONLINE
                fail_msg='Sent non-730 (RPL_MONONLINE) message after '
                'monitored nick “bar” connected: {msg}')
        self.assertEqual(len(m.params), 2, m,
                fail_msg='Invalid number of params of RPL_MONONLINE: {msg}')
        self.assertEqual(m.params[1].split('!')[0], 'bar',
                fail_msg='730 (RPL_MONONLINE) with bad target after “bar” '
                'connects: {msg}')
        self.assertIn('account', m.tags, m,
                fail_msg='730 (RPL_MONONLINE) sent because of logged in nick '
                'does not contain an account tag: {msg}')
        self.assertEqual(m.tags['account'], 'jilles', m,
                fail_msg='730 (RPL_MONONLINE) sent because of logged in nick '
                'does not contain the correct account tag (should be '
                '“jilles”): {msg}')
