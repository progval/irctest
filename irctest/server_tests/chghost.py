"""
<http://ircv3.net/specs/extensions/chghost.html>
"""

from irctest import cases
from irctest.irc_utils.sasl import sasl_plain_blob
from irctest.patma import ANYSTR, StrRe


@cases.mark_services
class ChghostServicesTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    def testChghostFromServices(self):
        self.connectClient("observer", capabilities=["chghost"], skip_if_cap_nak=True)
        self.connectClient("oldclient")

        self.controller.registerUser(
            self, "vhostuser", "sesame", vhost="vhost.example.com"
        )
        self.connectClient("vhost-user", capabilities=["sasl"], skip_if_cap_nak=True)

        for i in (1, 2, 3):
            self.sendLine(i, "JOIN #chan")
            self.getMessages(i)

        for i in (1, 2, 3):
            self.getMessages(i)

        self.sendLine(3, "AUTHENTICATE PLAIN")
        self.assertMessageMatch(
            self.getRegistrationMessage(3),
            command="AUTHENTICATE",
            params=["+"],
        )
        self.sendLine(3, sasl_plain_blob("vhostuser", "sesame"))
        self.assertMessageMatch(
            self.getRegistrationMessage(3),
            command="900",
        )

        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("vhost-user!.*@(?!vhost-user.example)"),
            command="CHGHOST",
            params=[ANYSTR, "vhost.example.com"],
        )
        self.assertEqual(self.getMessages(2), [])  # cycle?
