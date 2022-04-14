"""
`IRCv3 extended-join <https://ircv3.net/specs/extensions/extended-join>`_
"""

from irctest import cases


@cases.mark_services
class MetadataTestCase(cases.BaseServerTestCase):
    def connectRegisteredClient(self, nick):
        self.addClient()
        self.sendLine(2, "CAP LS 302")
        capabilities = self.getCapLs(2)
        assert "sasl" in capabilities
        self.requestCapabilities(2, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(2, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(2, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(
            m,
            command="900",
            fail_msg="Did not send 900 after correct SASL authentication.",
        )
        self.sendLine(2, "USER f * * :Realname")
        self.sendLine(2, "NICK {}".format(nick))
        self.sendLine(2, "CAP END")
        self.skipToWelcome(2)

    @cases.mark_capabilities("extended-join")
    def testNotLoggedIn(self):
        self.connectClient("foo", capabilities=["extended-join"], skip_if_cap_nak=True)
        self.joinChannel(1, "#chan")
        self.connectClient("bar")
        self.joinChannel(2, "#chan")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="JOIN",
            params=["#chan", "*", "Realname"],
            fail_msg="Expected “JOIN #chan * :Realname” after "
            "unregistered user joined, got: {msg}",
        )

    @cases.mark_capabilities("extended-join")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testLoggedIn(self):
        self.connectClient("foo", capabilities=["extended-join"], skip_if_cap_nak=True)
        self.joinChannel(1, "#chan")

        self.controller.registerUser(self, "jilles", "sesame")
        self.connectRegisteredClient("bar")
        self.joinChannel(2, "#chan")

        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="JOIN",
            params=["#chan", "jilles", "Realname"],
            fail_msg="Expected “JOIN #chan * :Realname” after "
            "nick “bar” logged in as “jilles” joined, got: {msg}",
        )
