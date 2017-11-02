"""
<http://ircv3.net/specs/extensions/tls-3.1.html>
"""

from irctest import cases
from irctest.basecontrollers import NotImplementedByController

class StarttlsFailTestCase(cases.BaseServerTestCase):
    @cases.SpecificationSelector.requiredBySpecification('IRCv3.1')
    def testStarttlsRequestTlsFail(self):
        """<http://ircv3.net/specs/extensions/tls-3.1.html>
        """
        self.addClient()

        # TODO: check also without this
        self.sendLine(1, 'CAP LS')
        capabilities = self.getCapLs(1)
        if 'tls' not in capabilities:
            raise NotImplementedByController('starttls')

        # TODO: check also without this
        self.sendLine(1, 'CAP REQ :tls')
        m = self.getRegistrationMessage(1)
        # TODO: Remove this once the trailing space issue is fixed in Charybdis
        # and Mammon:
        #self.assertMessageEqual(m, command='CAP', params=['*', 'ACK', 'tls'],
        #        fail_msg='Did not ACK capability `tls`: {msg}')
        self.sendLine(1, 'STARTTLS')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='691',
                fail_msg='Did not respond to STARTTLS with 691 whereas '
                'SSL is not configured: {msg}.')

class StarttlsTestCase(cases.BaseServerTestCase):
    ssl = True
    def testStarttlsRequestTls(self):
        """<http://ircv3.net/specs/extensions/tls-3.1.html>
        """
        self.addClient()

        # TODO: check also without this
        self.sendLine(1, 'CAP LS')
        capabilities = self.getCapLs(1)
        if 'tls' not in capabilities:
            raise NotImplementedByController('starttls')

        # TODO: check also without this
        self.sendLine(1, 'CAP REQ :tls')
        m = self.getRegistrationMessage(1)
        # TODO: Remove this one the trailing space issue is fixed in Charybdis
        # and Mammon:
        #self.assertMessageEqual(m, command='CAP', params=['*', 'ACK', 'tls'],
        #        fail_msg='Did not ACK capability `tls`: {msg}')
        self.sendLine(1, 'STARTTLS')
        m = self.getRegistrationMessage(1)
        self.assertMessageEqual(m, command='670',
                fail_msg='Did not respond to STARTTLS with 670: {msg}.')
        self.clients[1].starttls()
        self.sendLine(1, 'USER f * * :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP END')
        self.getMessages(1)
