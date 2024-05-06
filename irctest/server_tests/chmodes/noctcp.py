from irctest import cases, runner
from irctest.numerics import ERR_CANNOTSENDTOCHAN
from irctest.patma import ANYSTR


class NoctcpModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testNoctcpMode(self):
        """
        "This mode is used in almost all IRC software today. The standard mode letter
        used for it is `"+C"`.
        When this mode is set, should not send [CTCP](/ctcp.html) messages, except
        CTCP Action (also known as `/me`) to the channel.
        When blocking a message because of this mode, servers SHOULD use
        ERR_CANNOTSENDTOCHAN"
        -- TODO add link
        """
        self.connectClient("chanop")

        if "C" not in self.server_support.get("CHANMODES", ""):
            raise runner.NotImplementedByController("+C (noctcp) channel mode")

        # Both users join:

        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)  # synchronize

        self.connectClient("user")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)
        self.getMessages(1)

        # Send ACTION and PING, both should go through:

        self.sendLine(2, "PRIVMSG #chan :\x01ACTION is testing\x01")
        self.sendLine(2, "PRIVMSG #chan :\x01PING 12345\x01")
        self.assertEqual(self.getMessages(2), [])

        self.assertEqual(
            [(m.command, m.params[1]) for m in self.getMessages(1)],
            [
                ("PRIVMSG", "\x01ACTION is testing\x01"),
                ("PRIVMSG", "\x01PING 12345\x01"),
            ],
        )

        # Set mode +C:

        self.sendLine(1, "MODE #chan +C")
        self.getMessages(1)
        self.getMessages(2)

        # Send ACTION and PING, only ACTION should go through:

        self.sendLine(2, "PRIVMSG #chan :\x01ACTION is testing\x01")
        self.assertEqual(self.getMessages(2), [])
        self.sendLine(2, "PRIVMSG #chan :\x01PING 12345\x01")
        self.assertMessageMatch(
            self.getMessage(2),
            command=ERR_CANNOTSENDTOCHAN,
            params=["user", "#chan", ANYSTR],
        )

        self.assertEqual(
            [(m.command, m.params[1]) for m in self.getMessages(1)],
            [
                ("PRIVMSG", "\x01ACTION is testing\x01"),
            ],
        )
