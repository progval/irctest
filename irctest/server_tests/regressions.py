"""
Regression tests for bugs in `Ergo <https://ergo.chat/>`_.
"""

from irctest import cases
from irctest.numerics import (
    ERR_ERRONEUSNICKNAME,
    ERR_NICKNAMEINUSE,
    RPL_HELLO,
    RPL_WELCOME,
)
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

        # 'alice' is claimed, so 'Alice' is reserved and Bob cannot take it:
        self.sendLine(2, "NICK Alice")
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], command=ERR_NICKNAMEINUSE)

        # but alice can change case to 'Alice'; both alice and bob should get
        # a successful NICK line
        self.sendLine(1, "NICK Alice")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], nick="alice", command="NICK", params=["Alice"])
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageMatch(ms[0], nick="alice", command="NICK", params=["Alice"])

        # no responses, either to the user or to friends, from a no-op nick change
        self.sendLine(1, "NICK Alice")
        ms = self.getMessages(1)
        self.assertEqual(ms, [])
        ms = self.getMessages(2)
        self.assertEqual(ms, [])

    @cases.mark_specifications("RFC1459")
    @cases.xfailIfSoftware(["ngIRCd"], "wat")
    def testStarNick(self):
        self.addClient(1)
        self.sendLine(1, "NICK *")
        self.sendLine(1, "USER u s e r")
        replies = {"NOTICE"}
        while replies <= {"NOTICE", RPL_HELLO}:
            replies = set(msg.command for msg in self.getMessages(1, synchronize=False))
        self.assertIn(ERR_ERRONEUSNICKNAME, replies)
        self.assertNotIn(RPL_WELCOME, replies)

        self.sendLine(1, "NICK valid")
        replies = {"NOTICE"}
        while replies <= {"NOTICE", "PING"}:
            msgs = self.getMessages(1, synchronize=False)
            for msg in msgs:
                if msg.command == "PING":
                    # Hi Unreal
                    self.sendLine(1, "PONG :" + msg.params[0])
            replies = set(msg.command for msg in msgs)
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
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(m, command=RPL_WELCOME)

    @cases.mark_specifications("RFC1459")
    def testNickReleaseQuit(self):
        self.connectClient("alice")
        self.getMessages(1)
        self.sendLine(1, "QUIT")
        self.assertDisconnected(1)

        self.addClient(2)
        self.sendLine(2, "NICK alice")
        self.sendLine(2, "USER u s e r")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(m, command=RPL_WELCOME)
        self.sendLine(2, "QUIT")
        self.assertDisconnected(2)

        self.addClient(3)
        self.sendLine(3, "NICK ALICE")
        self.sendLine(3, "USER u s e r")
        m = self.getRegistrationMessage(3)
        self.assertMessageMatch(m, command=RPL_WELCOME)

    @cases.mark_specifications("Ergo")
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

    @cases.mark_specifications("IRCv3")
    def testLabeledNick(self):
        """
        InspIRCd up to 3.16.1 used the new nick as source of NICK changes

        https://github.com/inspircd/inspircd/issues/2067

        https://github.com/inspircd/inspircd/commit/83f01b36a11734fd91a4e7aad99c15463858fe4a
        """
        self.connectClient(
            "alice",
            capabilities=["batch", "labeled-response"],
            skip_if_cap_nak=True,
        )

        self.sendLine(1, "@label=abc NICK alice2")
        self.assertMessageMatch(
            self.getMessage(1),
            nick="alice",
            command="NICK",
            params=["alice2"],
            tags={"label": "abc", **ANYDICT},
        )
