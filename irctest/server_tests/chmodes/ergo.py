from irctest import cases
from irctest.numerics import ERR_CANNOTSENDTOCHAN, ERR_CHANOPRIVSNEEDED

MODERN_CAPS = [
    "server-time",
    "message-tags",
    "batch",
    "labeled-response",
    "echo-message",
    "account-tag",
]


@cases.mark_services
class RegisteredOnlySpeakMode(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testRegisteredOnlySpeakMode(self):
        self.controller.registerUser(self, "evan", "sesame")

        # test the +M (only registered users and ops can speak) channel mode
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +M")
        replies = self.getMessages("chanop")
        modeLines = [line for line in replies if line.command == "MODE"]
        self.assertMessageMatch(modeLines[0], command="MODE", params=["#chan", "+M"])

        self.connectClient("baz", name="baz")
        self.joinChannel("baz", "#chan")
        self.getMessages("chanop")
        # this message should be suppressed completely by +M
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        replies = self.getMessages("baz")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(ERR_CANNOTSENDTOCHAN, reply_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # +v exempts users from the registration requirement:
        self.sendLine("chanop", "MODE #chan +v baz")
        self.getMessages("chanop")
        self.getMessages("baz")
        self.sendLine("baz", "PRIVMSG #chan :hi again from baz")
        replies = self.getMessages("baz")
        # baz should not receive an error (or an echo)
        self.assertEqual(replies, [])
        replies = self.getMessages("chanop")
        self.assertMessageMatch(
            replies[0], command="PRIVMSG", params=["#chan", "hi again from baz"]
        )

        self.connectClient(
            "evan",
            name="evan",
            account="evan",
            password="sesame",
            capabilities=["sasl"],
        )
        self.joinChannel("evan", "#chan")
        self.getMessages("baz")
        self.sendLine("evan", "PRIVMSG #chan :hi from evan")
        replies = self.getMessages("evan")
        # evan should not receive an error (or an echo)
        self.assertEqual(replies, [])
        replies = self.getMessages("baz")
        self.assertMessageMatch(
            replies[0], command="PRIVMSG", params=["#chan", "hi from evan"]
        )


class OpModerated(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testOpModerated(self):
        # test the +U channel mode
        self.connectClient("chanop", name="chanop", capabilities=MODERN_CAPS)
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +U")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("baz", name="baz", capabilities=MODERN_CAPS)
        self.joinChannel("baz", "#chan")
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        echo = self.getMessages("baz")[0]
        self.assertMessageMatch(
            echo, command="PRIVMSG", params=["#chan", "hi from baz"]
        )
        self.assertEqual(
            [msg for msg in self.getMessages("chanop") if msg.command == "PRIVMSG"],
            [echo],
        )

        self.connectClient("qux", name="qux", capabilities=MODERN_CAPS)
        self.joinChannel("qux", "#chan")
        self.sendLine("qux", "PRIVMSG #chan :hi from qux")
        echo = self.getMessages("qux")[0]
        self.assertMessageMatch(
            echo, command="PRIVMSG", params=["#chan", "hi from qux"]
        )
        # message is relayed to chanop but not to unprivileged
        self.assertEqual(
            [msg for msg in self.getMessages("chanop") if msg.command == "PRIVMSG"],
            [echo],
        )
        self.assertEqual(
            [msg for msg in self.getMessages("baz") if msg.command == "PRIVMSG"], []
        )

        self.sendLine("chanop", "MODE #chan +v qux")
        self.getMessages("chanop")
        self.sendLine("qux", "PRIVMSG #chan :hi again from qux")
        echo = [msg for msg in self.getMessages("qux") if msg.command == "PRIVMSG"][0]
        self.assertMessageMatch(
            echo, command="PRIVMSG", params=["#chan", "hi again from qux"]
        )
        self.assertEqual(
            [msg for msg in self.getMessages("chanop") if msg.command == "PRIVMSG"],
            [echo],
        )
        self.assertEqual(
            [msg for msg in self.getMessages("baz") if msg.command == "PRIVMSG"], [echo]
        )
