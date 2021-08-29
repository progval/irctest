from irctest import cases, runner
from irctest.numerics import ERR_NOPRIVILEGES, ERR_UNKNOWNCOMMAND, RPL_YOUREOPER
from irctest.patma import ANYSTR, StrRe


class WallopsTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812", "Modern")
    def testWallops(self):
        """
        "The WALLOPS command is used to send a message to all currently connected
        users who have set the 'w' user mode for themselves."
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-4.7
        -- https://github.com/ircdocs/modern-irc/pull/118
        """
        self.connectClient("nick1")
        self.connectClient("nick2")
        self.connectClient("nick3")

        self.sendLine(2, "MODE nick2 -w")
        self.getMessages(2)
        self.sendLine(3, "MODE nick3 +w")
        self.getMessages(3)

        self.sendLine(1, "OPER operuser operpassword")
        self.assertIn(
            RPL_YOUREOPER,
            [m.command for m in self.getMessages(1)],
            fail_msg="OPER failed",
        )

        self.sendLine(1, "WALLOPS :hi everyone")

        messages = self.getMessages(1)
        if ERR_UNKNOWNCOMMAND in (message.command for message in messages):
            raise runner.NotImplementedByController("WALLOPS")
        for message in messages:
            self.assertMessageMatch(
                message,
                prefix=StrRe("nick1!.*"),
                command="WALLOPS",
                params=["hi everyone"],
            )

        self.assertMessageMatch(
            self.getMessage(3),
            prefix=StrRe("nick1!.*"),
            command="WALLOPS",
            params=["hi everyone"],
        )
        self.assertEqual(
            self.getMessages(2), [], fail_msg="Server sent WALLOPS to user without +w"
        )

    @cases.mark_specifications("Modern")
    def testWallopsPrivileges(self):
        """
        https://github.com/ircdocs/modern-irc/pull/118
        """
        self.connectClient("nick1")
        self.sendLine(1, "WALLOPS :hi everyone")
        self.assertMessageMatch(
            self.getMessage(1), command=ERR_NOPRIVILEGES, params=["nick1", ANYSTR]
        )
