from irctest import cases, runner
from irctest.numerics import ERR_CANNOTSENDTOCHAN, ERR_CHANOPRIVSNEEDED
from irctest.patma import ANYLIST, StrRe


class MuteExtbanTestCase(cases.BaseServerTestCase):
    """https://defs.ircdocs.horse/defs/isupport.html#extban

    It magically guesses what char the IRCd uses for mutes."""

    def char(self):
        if self.controller.extban_mute_char is None:
            raise runner.ExtbanNotSupported("", "mute")
        else:
            return self.controller.extban_mute_char

    @cases.mark_specifications("Ergo")
    def testISupport(self):
        self.connectClient(1)  # Fetches ISUPPORT
        isupport = self.server_support
        token = isupport["EXTBAN"]
        prefix, comma, types = token.partition(",")
        self.assertIn(self.char(), types, f"Missing '{self.char()}' in ISUPPORT EXTBAN")
        self.assertEqual(prefix, "")
        self.assertEqual(comma, ",")

    @cases.mark_specifications("ircdocs")
    def testMuteExtban(self):
        """Basic usage of mute"""
        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")
        if self.char() not in types:
            raise runner.ExtbanNotSupported(self.char(), "mute")

        clients = ("chanop", "bar")

        # Mute "bar"
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:bar!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("bar", name="bar", capabilities=["echo-message"])
        self.joinChannel("bar", "#chan")

        for client in clients:
            self.getMessages(client)

        # "bar" sees the MODE too
        self.sendLine("bar", "MODE #chan +b")
        self.assertMessageMatch(
            self.getMessage("bar"),
            command="367",
            params=[
                "bar",
                "#chan",
                f"{prefix}{self.char()}:bar!*@*",
                StrRe("chanop(!.*)?"),
                *ANYLIST,
            ],
        )
        self.getMessages("bar")

        # "bar" talks: rejected
        self.sendLine("bar", "PRIVMSG #chan :hi from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # remove mute on "bar" with -b
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan -b {prefix}{self.char()}:bar!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # "bar" can now talk
        self.sendLine("bar", "PRIVMSG #chan :hi again from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )

    @cases.mark_specifications("ircdocs")
    def testMuteExtbanVoiced(self):
        """Checks +v overrides the mute"""
        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")
        if self.char() not in types:
            raise runner.ExtbanNotSupported(self.char(), "mute")

        clients = ("chanop", "qux")

        # Mute "qux"
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:qux!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient(
            "qux", name="qux", ident="evan", capabilities=["echo-message"]
        )
        self.joinChannel("qux", "#chan")

        for client in clients:
            self.getMessages(client)

        # "qux" talks: rejected
        self.sendLine("qux", "PRIVMSG #chan :hi from qux")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        for client in clients:
            self.getMessages(client)

        # +v grants an exemption to +b
        self.sendLine("chanop", "MODE #chan +v qux")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # so "qux" can now talk
        self.sendLine("qux", "PRIVMSG #chan :hi again from qux")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )

    @cases.mark_specifications("ircdocs")
    def testMuteExtbanExempt(self):
        """Checks +e overrides the mute

        <https://defs.ircdocs.horse/defs/chanmodes.html#e-ban-exception>"""
        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")
        if self.char() not in types:
            raise runner.ExtbanNotSupported(self.char(), "mute")
        if "e" not in self.server_support["CHANMODES"]:
            raise runner.ChannelModeNotSupported(self.char(), "mute")

        clients = ("chanop", "qux")

        # Mute "qux"
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:qux!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient(
            "qux", name="qux", ident="evan", capabilities=["echo-message"]
        )
        self.joinChannel("qux", "#chan")

        for client in clients:
            self.getMessages(client)

        # "qux" talks: rejected
        self.sendLine("qux", "PRIVMSG #chan :hi from qux")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        for client in clients:
            self.getMessages(client)

        # +e grants an exemption to +b
        self.sendLine("chanop", f"MODE #chan +e {prefix}{self.char()}:*!~evan@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.getMessages("qux")

        # so "qux" can now talk
        self.sendLine("qux", "PRIVMSG #chan :thanks for mute-excepting me")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )

    @cases.mark_specifications("Ergo")
    def testCapitalization(self):
        """
        Regression test for oragono #1370: mutes not correctly enforced against
        users with capital letters in their NUH

        For consistency with regular -b, which allows unsetting up to
        normalization
        """
        clients = ("chanop", "bar")

        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")

        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:BAR!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("Bar", name="bar", capabilities=["echo-message"])
        self.joinChannel("bar", "#chan")

        for client in clients:
            self.getMessages(client)

        self.sendLine("bar", "PRIVMSG #chan :hi from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # remove mute with -b
        self.sendLine("chanop", f"MODE #chan -b {prefix}{self.char()}:bar!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # "bar" can talk again
        self.sendLine("bar", "PRIVMSG #chan :hi again from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )
