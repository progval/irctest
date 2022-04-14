"""
Roleplay features of `Ergo <https://ergo.chat/>`_
"""

from irctest import cases
from irctest.irc_utils.junkdrawer import random_name
from irctest.numerics import ERR_CANNOTSENDRP
from irctest.patma import StrRe


class RoleplayTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(ergo_roleplay=True)

    @cases.mark_specifications("Ergo")
    def testRoleplay(self):
        bar = random_name("bar")
        qux = random_name("qux")
        chan = random_name("#chan")
        self.connectClient(
            bar,
            name=bar,
            capabilities=["batch", "labeled-response", "message-tags", "server-time"],
        )
        self.connectClient(
            qux,
            name=qux,
            capabilities=["batch", "labeled-response", "message-tags", "server-time"],
        )
        self.joinChannel(bar, chan)
        self.joinChannel(qux, chan)
        self.getMessages(bar)

        # roleplay should be forbidden because we aren't +E yet
        self.sendLine(bar, "NPC %s bilbo too much bread" % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertEqual(reply.command, ERR_CANNOTSENDRP)

        self.sendLine(bar, "MODE %s +E" % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertEqual(reply.command, "MODE")
        self.assertMessageMatch(reply, command="MODE", params=[chan, "+E"])
        self.getMessages(qux)

        self.sendLine(bar, "NPC %s bilbo too much bread" % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertMessageMatch(
            reply, command="PRIVMSG", params=[chan, StrRe(".*too much bread.*")]
        )
        self.assertTrue(reply.prefix.startswith("*bilbo*!"))

        reply = self.getMessages(qux)[0]
        self.assertMessageMatch(
            reply, command="PRIVMSG", params=[chan, StrRe(".*too much bread.*")]
        )
        self.assertTrue(reply.prefix.startswith("*bilbo*!"))

        self.sendLine(bar, "SCENE %s dark and stormy night" % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertMessageMatch(
            reply, command="PRIVMSG", params=[chan, StrRe(".*dark and stormy night.*")]
        )
        self.assertTrue(reply.prefix.startswith("=Scene=!"))

        reply = self.getMessages(qux)[0]
        self.assertMessageMatch(
            reply, command="PRIVMSG", params=[chan, StrRe(".*dark and stormy night.*")]
        )
        self.assertTrue(reply.prefix.startswith("=Scene=!"))

        # test history storage
        self.sendLine(qux, "CHATHISTORY LATEST %s * 10" % (chan,))
        reply = [
            msg
            for msg in self.getMessages(qux)
            if msg.command == "PRIVMSG" and "bilbo" in msg.prefix
        ][0]
        self.assertMessageMatch(
            reply, command="PRIVMSG", params=[chan, StrRe(".*too much bread.*")]
        )
        self.assertTrue(reply.prefix.startswith("*bilbo*!"))
