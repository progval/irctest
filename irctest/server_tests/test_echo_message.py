"""
<http://ircv3.net/specs/extensions/echo-message-3.2.html>
"""

from irctest import cases
from irctest.basecontrollers import NotImplementedByController

class EchoMessageTestCase(cases.BaseServerTestCase):
    def _testEchoMessage(command, solo, server_time):
        @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
        def f(self):
            """<http://ircv3.net/specs/extensions/echo-message-3.2.html>
            """
            self.addClient()
            self.sendLine(1, 'CAP LS 302')
            capabilities = self.getCapLs(1)
            if 'echo-message' not in capabilities:
                raise NotImplementedByController('echo-message')
            if server_time and 'server-time' not in capabilities:
                raise NotImplementedByController('server-time')

            # TODO: check also without this
            self.sendLine(1, 'CAP REQ :echo-message{}'.format(
                ' server-time' if server_time else ''))
            m = self.getRegistrationMessage(1)
            # TODO: Remove this one the trailing space issue is fixed in Charybdis
            # and Mammon:
            #self.assertMessageEqual(m, command='CAP',
            #        params=['*', 'ACK', 'echo-message'] +
            #        (['server-time'] if server_time else []),
            #        fail_msg='Did not ACK advertised capabilities: {msg}')
            self.sendLine(1, 'USER f * * :foo')
            self.sendLine(1, 'NICK baz')
            self.sendLine(1, 'CAP END')
            self.skipToWelcome(1)
            self.getMessages(1)

            self.sendLine(1, 'JOIN #chan')

            if not solo:
                capabilities = ['server-time'] if server_time else None
                self.connectClient('qux', capabilities=capabilities)
                self.sendLine(2, 'JOIN #chan')

            # Synchronize and clean
            self.getMessages(1)
            if not solo:
                self.getMessages(2)
                self.getMessages(1)

            self.sendLine(1, '{} #chan :hello everyone'.format(command))
            m1 = self.getMessage(1)
            self.assertMessageEqual(m1, command=command,
                    params=['#chan', 'hello everyone'],
                    fail_msg='Did not echo “{} #chan :hello everyone”: {msg}',
                    extra_format=(command,))

            if not solo:
                m2 = self.getMessage(2)
                self.assertMessageEqual(m2, command=command,
                        params=['#chan', 'hello everyone'],
                        fail_msg='Did not propagate “{} #chan :hello everyone”: '
                        'after echoing it to the author: {msg}',
                        extra_format=(command,))
                self.assertEqual(m1.params, m2.params,
                        fail_msg='Parameters of forwarded and echoed '
                        'messages differ: {} {}',
                        extra_format=(m1, m2))
                if server_time:
                    self.assertEqual(m1.tags, m2.tags,
                            fail_msg='Tags of forwarded and echoed '
                            'messages differ: {} {}',
                            extra_format=(m1, m2))
        return f

    testEchoMessagePrivmsgNoServerTime = _testEchoMessage('PRIVMSG', False, False)
    testEchoMessagePrivmsgSolo = _testEchoMessage('PRIVMSG', True, True)
    testEchoMessagePrivmsg = _testEchoMessage('PRIVMSG', False, True)
    testEchoMessageNotice = _testEchoMessage('NOTICE', False, True)
