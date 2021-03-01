"""
Regression tests for bugs in oragono.
"""

from irctest import cases
from irctest.numerics import ERR_ERRONEUSNICKNAME, ERR_NICKNAMEINUSE, RPL_WELCOME
from irctest.patma import ANYDICT


class RegressionsTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459")
    def testFailedNickChange(self):
        # see oragono commit d0ded906d4ac8f
        self.connectClient("alice")
        self.connectClient("bob")

        # bob tries to change to an in-use nickname; this MUST fail
        self.sendLine(2, "NICK alice")
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], command=ERR_NICKNAMEINUSE)

        # bob MUST still own the bob nick, and be able to receive PRIVMSG as bob
        self.sendLine(1, "PRIVMSG bob hi")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 0)
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], command="PRIVMSG", params=["bob", "hi"])

    @cases.mark_specifications("RFC1459")
    def testCaseChanges(self):
        self.connectClient("alice")
        self.joinChannel(1, "#test")
        self.connectClient("bob")
        self.joinChannel(2, "#test")
        self.getMessages(1)
        self.getMessages(2)

        # case change: both alice and bob should get a successful nick line
        self.sendLine(1, "NICK Alice")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], command="NICK", params=["Alice"])
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], command="NICK", params=["Alice"])

        # no responses, either to the user or to friends, from a no-op nick change
        self.sendLine(1, "NICK Alice")
        ms = self.getMessages(1)
        self.assertEqual(ms, [])
        ms = self.getMessages(2)
        self.assertEqual(ms, [])

    @cases.mark_capabilities("message-tags", "batch", "echo-message", "server-time")
    def testTagCap(self):
        # regression test for oragono #754
        self.connectClient(
            "alice",
            capabilities=["message-tags", "batch", "echo-message", "server-time"],
            skip_if_cap_nak=True,
        )
        self.connectClient("bob")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(
            1, "@+draft/reply=ct95w3xemz8qj9du2h74wp8pee PRIVMSG bob :hey yourself"
        )
        self.assertMessageMatch(
            self.getMessage(1),
            command="PRIVMSG",
            params=["bob", "hey yourself"],
            tags={"+draft/reply": "ct95w3xemz8qj9du2h74wp8pee", **ANYDICT},
        )

        self.assertMessageMatch(
            self.getMessage(2),
            command="PRIVMSG",
            params=["bob", "hey yourself"],
            tags={},
        )

        self.sendLine(2, "CAP REQ :message-tags server-time")
        self.getMessages(2)
        self.sendLine(
            1, "@+draft/reply=tbxqauh9nykrtpa3n6icd9whan PRIVMSG bob :hey again"
        )
        self.getMessages(1)
        # now bob has the tags cap, so he should receive the tags
        self.assertMessageMatch(
            self.getMessage(2),
            command="PRIVMSG",
            params=["bob", "hey again"],
            tags={"+draft/reply": "tbxqauh9nykrtpa3n6icd9whan", **ANYDICT},
        )

    @cases.mark_specifications("RFC1459")
    def testStarNick(self):
        self.addClient(1)
        self.sendLine(1, "NICK *")
        self.sendLine(1, "USER u s e r")
        replies = {"NOTICE"}
        while replies == {"NOTICE"}:
            replies = set(msg.command for msg in self.getMessages(1, synchronize=False))
        self.assertIn(ERR_ERRONEUSNICKNAME, replies)
        self.assertNotIn(RPL_WELCOME, replies)

        self.sendLine(1, "NICK valid")
        replies = {"NOTICE"}
        while replies <= {"NOTICE"}:
            replies = set(msg.command for msg in self.getMessages(1, synchronize=False))
        self.assertNotIn(ERR_ERRONEUSNICKNAME, replies)
        self.assertIn(RPL_WELCOME, replies)

    @cases.mark_specifications("RFC1459")
    def testEmptyNick(self):
        self.addClient(1)
        self.sendLine(1, "NICK :")
        self.sendLine(1, "USER u s e r")
        replies = {"NOTICE"}
        while replies == {"NOTICE"}:
            replies = set(msg.command for msg in self.getMessages(1, synchronize=False))
        self.assertNotIn(RPL_WELCOME, replies)

    @cases.mark_specifications("RFC1459")
    def testNickRelease(self):
        # regression test for oragono #1252
        self.connectClient("alice")
        self.getMessages(1)
        self.sendLine(1, "NICK malice")
        nick_msgs = [msg for msg in self.getMessages(1) if msg.command == "NICK"]
        self.assertEqual(len(nick_msgs), 1)
        self.assertMessageMatch(nick_msgs[0], command="NICK", params=["malice"])

        self.addClient(2)
        self.sendLine(2, "NICK alice")
        self.sendLine(2, "USER u s e r")
        replies = set(msg.command for msg in self.getMessages(2))
        self.assertNotIn(ERR_NICKNAMEINUSE, replies)
        self.assertIn(RPL_WELCOME, replies)

    @cases.mark_specifications("RFC1459")
    def testNickReleaseQuit(self):
        self.connectClient("alice")
        self.getMessages(1)
        self.sendLine(1, "QUIT")
        self.assertDisconnected(1)

        self.addClient(2)
        self.sendLine(2, "NICK alice")
        self.sendLine(2, "USER u s e r")
        replies = set(msg.command for msg in self.getMessages(2))
        self.assertNotIn(ERR_NICKNAMEINUSE, replies)
        self.assertIn(RPL_WELCOME, replies)
        self.sendLine(2, "QUIT")
        self.assertDisconnected(2)

        self.addClient(3)
        self.sendLine(3, "NICK ALICE")
        self.sendLine(3, "USER u s e r")
        replies = set(msg.command for msg in self.getMessages(3))
        self.assertNotIn(ERR_NICKNAMEINUSE, replies)
        self.assertIn(RPL_WELCOME, replies)

    @cases.mark_specifications("RFC1459")
    def testNickReleaseUnregistered(self):
        self.addClient(1)
        self.sendLine(1, "NICK alice")
        self.sendLine(1, "QUIT")
        self.assertDisconnected(1)

        self.addClient(2)
        self.sendLine(2, "NICK alice")
        self.sendLine(2, "USER u s e r")
        reply = self.getRegistrationMessage(2)
        self.assertMessageMatch(reply, command=RPL_WELCOME)
