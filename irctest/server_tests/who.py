import re

import pytest

from irctest import cases
from irctest.numerics import RPL_ENDOFWHO, RPL_WHOREPLY, RPL_YOUREOPER
from irctest.patma import ANYSTR, InsensitiveStr, StrRe


def realname_regexp(realname):
    return (
        "[0-9]+ "  # is 0 for every IRCd I can find, except ircu2 (which returns 3)
        + "(0042 )?"  # for irc2...
        + re.escape(realname)
    )


class WhoTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    def _init(self):
        self.nick = "coolNick"
        self.username = "myusernam"  # may be truncated if longer than this
        self.realname = "My UniqueReal Name"

        self.addClient()
        self.sendLine(1, f"NICK {self.nick}")
        self.sendLine(1, f"USER {self.username} 0 * :{self.realname}")
        self.skipToWelcome(1)
        self.sendLine(1, "JOIN #chan")

        self.getMessages(1)

        self.connectClient("otherNick")
        self.getMessages(2)
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)

    def _checkReply(self, reply, flags):
        host_re = "[0-9A-Za-z_:.-]+"
        if reply.params[1] == "*":
            # Unreal, ...
            self.assertMessageMatch(
                reply,
                command=RPL_WHOREPLY,
                params=[
                    "otherNick",
                    "*",  # no chan
                    StrRe("~?" + self.username),
                    StrRe(host_re),
                    "My.Little.Server",
                    "coolNick",
                    flags,
                    StrRe(realname_regexp(self.realname)),
                ],
            )
        else:
            # Solanum, Insp, ...
            self.assertMessageMatch(
                reply,
                command=RPL_WHOREPLY,
                params=[
                    "otherNick",
                    "#chan",
                    StrRe("~?" + self.username),
                    StrRe(host_re),
                    "My.Little.Server",
                    "coolNick",
                    flags + "@",
                    StrRe(realname_regexp(self.realname)),
                ],
            )

    @cases.mark_specifications("Modern")
    def testWhoStar(self):
        self._init()

        self.sendLine(2, "WHO *")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 3, "Unexpected number of messages")

        (*replies, end) = messages

        # Get them in deterministic order
        replies.sort(key=lambda msg: msg.params[5])

        self._checkReply(replies[0], "H")

        # " `<mask>` MUST be exactly the `<mask>` parameter sent by the client
        # in its `WHO` message. This means the case MUST be preserved."
        # -- https://github.com/ircdocs/modern-irc/pull/138/files
        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", "*", ANYSTR],
        )

    @pytest.mark.parametrize(
        "mask", ["coolNick", "coolnick", "coolni*"], ids=["exact", "casefolded", "mask"]
    )
    @cases.mark_specifications("Modern")
    def testWhoNick(self, mask):
        self._init()

        self.sendLine(2, f"WHO {mask}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self._checkReply(reply, "H")

        # " `<mask>` MUST be exactly the `<mask>` parameter sent by the client
        # in its `WHO` message. This means the case MUST be preserved."
        # -- https://github.com/ircdocs/modern-irc/pull/138/files
        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr(mask), ANYSTR],
        )

    @pytest.mark.skip("Not consistently implemented")
    @pytest.mark.parametrize(
        "mask",
        ["*usernam", "*UniqueReal*", "127.0.0.1"],
        ids=["username", "realname-mask", "hostname"],
    )
    def testWhoUsernameRealName(self, mask):
        self._init()

        self.sendLine(2, f"WHO :{mask}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self._checkReply(reply, "H")

        # " `<mask>` MUST be exactly the `<mask>` parameter sent by the client
        # in its `WHO` message. This means the case MUST be preserved."
        # -- https://github.com/ircdocs/modern-irc/pull/138/files
        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr(mask), ANYSTR],
        )

    @pytest.mark.skip("Not consistently implemented")
    def testWhoRealNameSpaces(self):
        self._init()

        self.sendLine(2, "WHO :*UniqueReal Name")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self._checkReply(reply, "H")

        # What to do here? This?
        # self.assertMessageMatch(
        #     end,
        #     command=RPL_ENDOFWHO,
        #     params=[
        #         "otherNick",
        #         InsensitiveStr("*UniqueReal"),
        #         InsensitiveStr("Name"),
        #         ANYSTR,
        #     ],
        # )

    @pytest.mark.parametrize(
        "mask", ["coolNick", "coolnick", "coolni*"], ids=["exact", "casefolded", "mask"]
    )
    @cases.mark_specifications("Modern")
    def testWhoNickAway(self, mask):
        self._init()

        self.sendLine(1, "AWAY :be right back")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(2, f"WHO {mask}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self._checkReply(reply, "G")

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr(mask), ANYSTR],
        )

    @pytest.mark.parametrize(
        "mask", ["coolNick", "coolnick", "coolni*"], ids=["exact", "casefolded", "mask"]
    )
    @cases.mark_specifications("Modern")
    def testWhoNickOper(self, mask):
        self._init()

        self.sendLine(1, "OPER operuser operpassword")
        self.assertIn(
            RPL_YOUREOPER,
            [m.command for m in self.getMessages(1)],
            fail_msg="OPER failed",
        )

        self.getMessages(2)

        self.sendLine(2, f"WHO {mask}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self._checkReply(reply, "H*")

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr(mask), ANYSTR],
        )

    @pytest.mark.parametrize(
        "mask", ["coolNick", "coolnick", "coolni*"], ids=["exact", "casefolded", "mask"]
    )
    @cases.mark_specifications("Modern")
    def testWhoNickAwayAndOper(self, mask):
        self._init()

        self.sendLine(1, "OPER operuser operpassword")
        self.assertIn(
            RPL_YOUREOPER,
            [m.command for m in self.getMessages(1)],
            fail_msg="OPER failed",
        )

        self.sendLine(1, "AWAY :be right back")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(2, f"WHO {mask}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self._checkReply(reply, "G*")

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr(mask), ANYSTR],
        )

    @pytest.mark.parametrize("mask", ["#chan", "#CHAN"], ids=["exact", "casefolded"])
    @cases.mark_specifications("Modern")
    def testWhoChan(self, mask):
        self._init()

        self.sendLine(1, "OPER operuser operpassword")
        self.assertIn(
            RPL_YOUREOPER,
            [m.command for m in self.getMessages(1)],
            fail_msg="OPER failed",
        )

        self.sendLine(1, "AWAY :be right back")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(2, f"WHO {mask}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 3, "Unexpected number of messages")

        (*replies, end) = messages

        # Get them in deterministic order
        replies.sort(key=lambda msg: msg.params[5])

        host_re = "[0-9A-Za-z_:.-]+"
        self.assertMessageMatch(
            replies[0],
            command=RPL_WHOREPLY,
            params=[
                "otherNick",
                "#chan",
                StrRe("~?" + self.username),
                StrRe(host_re),
                "My.Little.Server",
                "coolNick",
                "G*@",
                StrRe(realname_regexp(self.realname)),
            ],
        )

        self.assertMessageMatch(
            replies[1],
            command=RPL_WHOREPLY,
            params=[
                "otherNick",
                "#chan",
                ANYSTR,
                ANYSTR,
                "My.Little.Server",
                "otherNick",
                "H",
                StrRe("[0-9]+ .*"),
            ],
        )

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr(mask), ANYSTR],
        )
