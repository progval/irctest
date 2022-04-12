"""
`IRCv3 account-tag <https://ircv3.net/specs/extensions/account-tag>`_
"""

from irctest import cases


@cases.mark_services
class AccountTagTestCase(cases.BaseServerTestCase):
    def connectRegisteredClient(self, nick):
        self.addClient()
        self.sendLine(2, "CAP LS 302")
        capabilities = self.getCapLs(2)
        assert "sasl" in capabilities

        self.sendLine(2, "USER f * * :Realname")
        self.sendLine(2, "NICK {}".format(nick))
        self.sendLine(2, "CAP REQ :sasl")
        self.getRegistrationMessage(2)

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

    @cases.mark_capabilities("account-tag")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPrivmsg(self):
        self.connectClient("foo", capabilities=["account-tag"], skip_if_cap_nak=True)
        self.getMessages(1)
        self.controller.registerUser(self, "jilles", "sesame")
        self.connectRegisteredClient("bar")
        self.sendLine(2, "PRIVMSG foo :hi")
        self.getMessages(2)
        m = self.getMessage(1)
        self.assertMessageMatch(
            m, command="PRIVMSG", params=["foo", "hi"], tags={"account": "jilles"}
        )

    @cases.mark_capabilities("account-tag")
    @cases.skipUnlessHasMechanism("PLAIN")
    @cases.xfailIfSoftware(
        ["Charybdis"], "https://github.com/solanum-ircd/solanum/issues/166"
    )
    def testInvite(self):
        self.connectClient("foo", capabilities=["account-tag"], skip_if_cap_nak=True)
        self.getMessages(1)
        self.controller.registerUser(self, "jilles", "sesame")
        self.connectRegisteredClient("bar")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)
        self.sendLine(2, "INVITE foo #chan")
        self.getMessages(2)
        m = self.getMessage(1)
        self.assertMessageMatch(
            m, command="INVITE", params=["foo", "#chan"], tags={"account": "jilles"}
        )
