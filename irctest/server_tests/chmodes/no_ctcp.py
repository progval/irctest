from irctest import cases
from irctest.numerics import ERR_CANNOTSENDTOCHAN


class NoCTCPChannelModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testNoCTCPChannelMode(self):
        """Test Ergo's +C channel mode that blocks CTCPs."""
        self.connectClient("bar")
        self.joinChannel(1, "#chan")
        self.sendLine(1, "MODE #chan +C")
        self.getMessages(1)

        self.connectClient("qux")
        self.joinChannel(2, "#chan")
        self.getMessages(2)

        self.sendLine(1, "PRIVMSG #chan :\x01ACTION hi\x01")
        self.getMessages(1)
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(
            ms[0], command="PRIVMSG", params=["#chan", "\x01ACTION hi\x01"]
        )

        self.sendLine(1, "PRIVMSG #chan :\x01PING 1473523796 918320\x01")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], command=ERR_CANNOTSENDTOCHAN)
        ms = self.getMessages(2)
        self.assertEqual(ms, [])
