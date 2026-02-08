"""
STATUSMSG ISUPPORT token and related PRIVMSG (`Modern
<https://modern.ircdocs.horse/#statusmsg-parameter>`__)

TODO: cross-reference Modern
"""

from irctest import cases, runner
from irctest.numerics import RPL_NAMREPLY
from irctest.specifications import IsupportTokens


class StatusmsgTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testInIsupport(self):
        """Check that the expected STATUSMSG parameter appears in our isupport list."""
        self.connectClient("foo")  # detects ISUPPORT
        self.assertEqual(self.server_support["STATUSMSG"], "~&@%+")

    @cases.mark_isupport("STATUSMSG")
    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "snircd"],
        "STATUSMSG is present in ISUPPORT, but it not actually supported as PRIVMSG "
        "target (only for WALLCOPS/WALLCHOPS/...)",
    )
    def testStatusmsgFromOp(self):
        """Test that STATUSMSG are sent to the intended recipients,
        with the intended prefixes."""
        self.connectClient("chanop")
        self.joinChannel(1, "#chan")
        self.getMessages(1)

        if "@" not in self.server_support.get("STATUSMSG", ""):
            raise runner.IsupportTokenNotSupported(IsupportTokens.STATUSMSG)

        self.connectClient("joe")
        self.joinChannel(2, "#chan")
        self.getMessages(2)

        self.connectClient("schmoe")
        self.sendLine(3, "join #chan")

        messages = self.getMessages(3)
        names = set()
        for message in messages:
            if message.command == RPL_NAMREPLY:
                names.update(set(message.params[-1].split()))
        # chanop should be opped
        self.assertEqual(
            names, {"@chanop", "joe", "schmoe"}, f"unexpected names: {names}"
        )

        self.sendLine(1, "MODE #chan +o schmoe")
        self.getMessages(1)

        self.getMessages(3)
        self.sendLine(3, "privmsg @#chan :this message is for operators")
        self.assertEqual(
            self.getMessages(3),
            [],
            fail_msg="PRIVMSG @#chan from channel op was refused",
        )

        # check the operator's messages
        statusMsg = self.getMessage(1, filter_pred=lambda m: m.command == "PRIVMSG")
        self.assertMessageMatch(
            statusMsg, params=["@#chan", "this message is for operators"]
        )

        # check the non-operator's messages
        unprivilegedMessages = [
            msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"
        ]
        self.assertEqual(len(unprivilegedMessages), 0)

    @cases.mark_isupport("STATUSMSG")
    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "snircd"],
        "STATUSMSG is present in ISUPPORT, but it not actually supported as PRIVMSG "
        "target (only for WALLCOPS/WALLCHOPS/...)",
    )
    def testStatusmsgFromRegular(self):
        """Test that STATUSMSG are sent to the intended recipients,
        with the intended prefixes."""
        self.connectClient("chanop")
        self.joinChannel(1, "#chan")
        self.getMessages(1)

        if "@" not in self.server_support.get("STATUSMSG", ""):
            raise runner.IsupportTokenNotSupported(IsupportTokens.STATUSMSG)

        self.connectClient("joe")
        self.joinChannel(2, "#chan")
        self.getMessages(2)

        self.connectClient("schmoe")
        self.sendLine(3, "join #chan")
        messages = self.getMessages(3)
        names = set()
        for message in messages:
            if message.command == RPL_NAMREPLY:
                names.update(set(message.params[-1].split()))
        # chanop should be opped
        self.assertEqual(
            names, {"@chanop", "joe", "schmoe"}, f"unexpected names: {names}"
        )

        self.getMessages(3)
        self.sendLine(3, "privmsg @#chan :this message is for operators")
        if self.getMessages(3) != []:
            raise runner.ImplementationChoice(
                "Regular users can not send PRIVMSG @#chan"
            )

        # check the operator's messages
        statusMsg = self.getMessage(1, filter_pred=lambda m: m.command == "PRIVMSG")
        self.assertMessageMatch(
            statusMsg, params=["@#chan", "this message is for operators"]
        )

        # check the non-operator's messages
        unprivilegedMessages = [
            msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"
        ]
        self.assertEqual(len(unprivilegedMessages), 0)
