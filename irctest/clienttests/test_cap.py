from irctest.cases import ClientTestCase

class CapTestCase(ClientTestCase):
    def testSendCap(self):
        (hostname, port) = self.server.getsockname()
        self.controller.run(
                hostname=hostname,
                port=port,
                authentication=None,
                )
        self.acceptClient()
        print(self.getLine())
