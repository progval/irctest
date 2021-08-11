from irctest import cases
from irctest.numerics import RPL_AWAY, RPL_NOWAWAY, RPL_UNAWAY


class AwayTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812")
    def testAway(self):
        self.connectClient("bar")
        self.sendLine(1, "AWAY :I'm not here right now")
        replies = self.getMessages(1)
        self.assertIn(RPL_NOWAWAY, [msg.command for msg in replies])

        self.connectClient("qux")
        self.sendLine(2, "PRIVMSG bar :what's up")
        self.assertMessageMatch(
            self.getMessage(2),
            command=RPL_AWAY,
            params=["qux", "bar", "I'm not here right now"],
        )

        self.sendLine(1, "AWAY")
        replies = self.getMessages(1)
        self.assertIn(RPL_UNAWAY, [msg.command for msg in replies])

        self.sendLine(2, "PRIVMSG bar :what's up")
        replies = self.getMessages(2)
        self.assertEqual(len(replies), 0)
