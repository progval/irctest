"""
<http://ircv3.net/specs/extensions/echo-message-3.2.html>
"""

from irctest import cases
from irctest.basecontrollers import NotImplementedByController

class EchoMessageTestCase(cases.BaseServerTestCase):
    def _testEchoMessage(command, solo):
        @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
        def f(self):
            """<http://ircv3.net/specs/extensions/echo-message-3.2.html>
            """
            print('------'*100)
            self.addClient()
            self.sendLine(1, 'CAP LS 302')
            capabilities = self.getCapLs(1)
            if 'echo-message' not in capabilities:
                raise NotImplementedByController('echo-message')

            # TODO: check also without this
            self.sendLine(1, 'CAP REQ :echo-message')
            m = self.getRegistrationMessage(1)
            # TODO: Remove this one the trailing space issue is fixed in Charybdis
            # and Mammon:
            #self.assertMessageEqual(m, command='CAP',
            #        params=['*', 'ACK', 'echo-message'],
            #        fail_msg='Did not ACK capability `echo-message`: {msg}')
            self.sendLine(1, 'USER f * * :foo')
            self.sendLine(1, 'NICK baz')
            self.sendLine(1, 'CAP END')
            self.skipToWelcome(1)
            self.getMessages(1)

            self.sendLine(1, 'JOIN #chan')

            if not solo:
                self.connectClient('qux')
                self.sendLine(2, 'JOIN #chan')

            # Synchronize and clean
            self.getMessages(1)
            if not solo:
                self.getMessages(2)
                self.getMessages(1)

            self.sendLine(1, '{} #chan :hello everyone'.format(command))
            m = self.getMessage(1)
            self.assertMessageEqual(m, command=command,
                    params=['#chan', 'hello everyone'],
                    fail_msg='Did not echo “{} #chan :hello everyone”: {msg}',
                    extra_format=(command,))

            if not solo:
                m = self.getMessage(2)
                self.assertMessageEqual(m, command=command,
                        params=['#chan', 'hello everyone'],
                        fail_msg='Did not propagate “{} #chan :hello everyone”: '
                        'after echoing it to the author: {msg}',
                        extra_format=(command,))
        return f

    testEchoMessagePrivmsg = _testEchoMessage('PRIVMSG', False)
    testEchoMessagePrivmsgSolo = _testEchoMessage('PRIVMSG', True)
    testEchoMessageNotice = _testEchoMessage('NOTICE', False)
