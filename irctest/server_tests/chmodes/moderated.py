from irctest import cases
from irctest.numerics import ERR_CANNOTSENDTOCHAN


class ModeratedMode(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812")
    def testModeratedMode(self):
        # test the +m channel mode
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +m")
        replies = self.getMessages("chanop")
        modeLines = [line for line in replies if line.command == "MODE"]
        self.assertMessageMatch(modeLines[0], command="MODE", params=["#chan", "+m"])

        self.connectClient("baz", name="baz")
        self.joinChannel("baz", "#chan")
        self.getMessages("chanop")
        # this message should be suppressed completely by +m
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        replies = self.getMessages("baz")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(ERR_CANNOTSENDTOCHAN, reply_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # grant +v, user should be able to send messages
        self.sendLine("chanop", "MODE #chan +v baz")
        self.getMessages("chanop")
        self.getMessages("baz")
        self.sendLine("baz", "PRIVMSG #chan :hi again from baz")
        self.getMessages("baz")
        relays = self.getMessages("chanop")
        relay = relays[0]
        self.assertMessageMatch(
            relay, command="PRIVMSG", params=["#chan", "hi again from baz"]
        )
