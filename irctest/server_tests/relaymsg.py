"""
RELAYMSG command of `Ergo <https://ergo.chat/>`_
"""

from irctest import cases
from irctest.irc_utils.junkdrawer import random_name
from irctest.patma import ANYSTR
from irctest.server_tests.chathistory import CHATHISTORY_CAP, EVENT_PLAYBACK_CAP

RELAYMSG_CAP = "draft/relaymsg"
RELAYMSG_TAG_NAME = "draft/relaymsg"


class RelaymsgTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(chathistory=True)

    @cases.mark_specifications("Ergo")
    def testRelaymsg(self):
        self.connectClient(
            "baz",
            name="baz",
            capabilities=[
                "batch",
                "labeled-response",
                "echo-message",
                CHATHISTORY_CAP,
                EVENT_PLAYBACK_CAP,
            ],
        )
        self.connectClient(
            "qux",
            name="qux",
            capabilities=[
                "batch",
                "labeled-response",
                "echo-message",
                CHATHISTORY_CAP,
                EVENT_PLAYBACK_CAP,
            ],
        )
        chname = random_name("#relaymsg")
        self.joinChannel("baz", chname)
        self.joinChannel("qux", chname)
        self.getMessages("baz")
        self.getMessages("qux")

        self.sendLine("baz", "RELAYMSG %s invalid!nick/discord hi" % (chname,))
        self.assertMessageMatch(
            self.getMessages("baz")[0],
            command="FAIL",
            params=["RELAYMSG", "INVALID_NICK", ANYSTR],
        )

        self.sendLine("baz", "RELAYMSG %s regular_nick hi" % (chname,))
        self.assertMessageMatch(
            self.getMessages("baz")[0],
            command="FAIL",
            params=["RELAYMSG", "INVALID_NICK", ANYSTR],
        )

        self.sendLine("baz", "RELAYMSG %s smt/discord hi" % (chname,))
        response = self.getMessages("baz")[0]
        self.assertMessageMatch(
            response, nick="smt/discord", command="PRIVMSG", params=[chname, "hi"]
        )
        relayed_msg = self.getMessages("qux")[0]
        self.assertMessageMatch(
            relayed_msg, nick="smt/discord", command="PRIVMSG", params=[chname, "hi"]
        )

        # labeled-response
        self.sendLine("baz", "@label=x RELAYMSG %s smt/discord :hi again" % (chname,))
        response = self.getMessages("baz")[0]
        self.assertMessageMatch(
            response,
            nick="smt/discord",
            command="PRIVMSG",
            params=[chname, "hi again"],
            tags={"label": "x"},
        )
        relayed_msg = self.getMessages("qux")[0]
        self.assertMessageMatch(
            relayed_msg,
            nick="smt/discord",
            command="PRIVMSG",
            params=[chname, "hi again"],
        )

        self.sendLine("qux", "RELAYMSG %s smt/discord :hi a third time" % (chname,))
        self.assertMessageMatch(
            self.getMessages("qux")[0],
            command="FAIL",
            params=["RELAYMSG", "PRIVS_NEEDED", ANYSTR],
        )

        # grant qux chanop, allowing relaymsg
        self.sendLine("baz", "MODE %s +o qux" % (chname,))
        self.getMessages("baz")
        self.getMessages("qux")
        # give baz the relaymsg cap
        self.sendLine("baz", "CAP REQ %s" % (RELAYMSG_CAP))
        self.assertMessageMatch(
            self.getMessages("baz")[0],
            command="CAP",
            params=["baz", "ACK", RELAYMSG_CAP],
        )

        self.sendLine("qux", "RELAYMSG %s smt/discord :hi a third time" % (chname,))
        response = self.getMessages("qux")[0]
        self.assertMessageMatch(
            response,
            nick="smt/discord",
            command="PRIVMSG",
            params=[chname, "hi a third time"],
        )
        relayed_msg = self.getMessages("baz")[0]
        self.assertMessageMatch(
            relayed_msg,
            nick="smt/discord",
            command="PRIVMSG",
            params=[chname, "hi a third time"],
            tags={RELAYMSG_TAG_NAME: "qux"},
        )

        self.sendLine("baz", "CHATHISTORY LATEST %s * 10" % (chname,))
        messages = self.getMessages("baz")
        self.assertEqual(
            [msg.params[-1] for msg in messages if msg.command == "PRIVMSG"],
            ["hi", "hi again", "hi a third time"],
        )
