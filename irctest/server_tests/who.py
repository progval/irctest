"""
The WHO command  (`Modern <https://modern.ircdocs.horse/#who-message>`__)
and `IRCv3 WHOX <https://ircv3.net/specs/extensions/whox>`_

TODO: cross-reference RFC 1459 and RFC 2812
"""

import re

import pytest

from irctest import cases, runner
from irctest.numerics import RPL_ENDOFWHO, RPL_WHOREPLY, RPL_WHOSPCRPL, RPL_YOUREOPER
from irctest.patma import ANYSTR, Either, InsensitiveStr, StrRe


def realname_regexp(realname):
    return (
        "[0-9]+ "  # is 0 for every IRCd I can find, except ircu2 (which returns 3)
        + "(0042 )?"  # for irc2...
        + re.escape(realname)
    )


class BaseWhoTestCase:
    def _init(self, auth=False):
        self.nick = "coolNick"
        self.username = "myusernam"  # may be truncated if longer than this
        self.realname = "My UniqueReal Name"

        self.addClient()
        if auth:
            self.controller.registerUser(self, "coolAcct", "sesame")
            self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=True)
            self.authenticateClient(1, "coolAcct", "sesame")
        self.sendLine(1, f"NICK {self.nick}")
        self.sendLine(1, f"USER {self.username} 0 * :{self.realname}")
        if auth:
            self.sendLine(1, "CAP END")
        self.skipToWelcome(1)
        self.getMessages(1)
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
                    Either("My.Little.Server", "*"),
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
                    Either("My.Little.Server", "*"),
                    "coolNick",
                    flags + "@",
                    StrRe(realname_regexp(self.realname)),
                ],
            )


class WhoTestCase(BaseWhoTestCase, cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testWhoStar(self):
        if self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

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
        if "*" in mask and self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

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
        if "*" in mask and self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

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
        if "*" in mask and self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

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
    @cases.xfailIfSoftware(
        ["Sable"],
        "Sable does not advertise oper status in WHO: "
        "https://github.com/Libera-Chat/sable/pull/77",
    )
    @cases.mark_specifications("Modern")
    def testWhoNickOper(self, mask):
        if "*" in mask and self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

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
    @cases.xfailIfSoftware(
        ["Sable"],
        "Sable does not advertise oper status in WHO: "
        "https://github.com/Libera-Chat/sable/pull/77",
    )
    @cases.mark_specifications("Modern")
    def testWhoNickAwayAndOper(self, mask):
        if "*" in mask and self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

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
        if "*" in mask and self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

        self._init()

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
                Either("My.Little.Server", "*"),
                "coolNick",
                "G@",
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
                Either("My.Little.Server", "*"),
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

    @cases.mark_specifications("Modern")
    def testWhoMultiChan(self):
        """
        When WHO <#chan> is sent, the second parameter of RPL_WHOREPLY must
        be ``#chan``. See discussion on Modern:
        <https://github.com/ircdocs/modern-irc/issues/209>
        """
        self._init()

        self.sendLine(1, "JOIN #otherchan")
        self.getMessages(1)

        self.sendLine(2, "JOIN #otherchan")
        self.getMessages(2)

        for chan in ["#chan", "#otherchan"]:
            self.sendLine(2, f"WHO {chan}")
            messages = self.getMessages(2)

            self.assertEqual(len(messages), 3, "Unexpected number of messages")

            (*replies, end) = messages

            # Get them in deterministic order
            replies.sort(key=lambda msg: msg.params[5])

            self.assertMessageMatch(
                replies[0],
                command=RPL_WHOREPLY,
                params=[
                    "otherNick",
                    chan,
                    ANYSTR,
                    ANYSTR,
                    Either("My.Little.Server", "*"),
                    "coolNick",
                    ANYSTR,
                    ANYSTR,
                ],
            )

            self.assertMessageMatch(
                replies[1],
                command=RPL_WHOREPLY,
                params=[
                    "otherNick",
                    chan,
                    ANYSTR,
                    ANYSTR,
                    Either("My.Little.Server", "*"),
                    "otherNick",
                    ANYSTR,
                    ANYSTR,
                ],
            )

            self.assertMessageMatch(
                end,
                command=RPL_ENDOFWHO,
                params=["otherNick", InsensitiveStr(chan), ANYSTR],
            )

    @cases.mark_specifications("Modern")
    def testWhoNickNotExists(self):
        """
        When WHO is sent with a non-existing nickname, the server must reply
        with a single RPL_ENDOFWHO. See:
        <https://github.com/ircdocs/modern-irc/pull/216>
        """

        self._init()

        self.sendLine(2, "WHO idontexist")
        (end,) = self.getMessages(2)

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr("idontexist"), ANYSTR],
        )

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("WHOX")
    def testWhoxFull(self):
        """https://github.com/ircv3/ircv3-specifications/pull/482"""
        self._testWhoxFull("%tcuihsnfdlaor,123")

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("WHOX")
    def testWhoxFullReversed(self):
        """https://github.com/ircv3/ircv3-specifications/pull/482"""
        self._testWhoxFull("%" + "".join(reversed("tcuihsnfdlaor")) + ",123")

    def _testWhoxFull(self, chars):
        self._init()
        if "WHOX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("WHOX")

        self.sendLine(2, f"WHO coolNick {chars}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self.assertMessageMatch(
            reply,
            command=RPL_WHOSPCRPL,
            params=[
                "otherNick",
                "123",
                Either("#chan", "*"),
                StrRe("~?myusernam"),
                ANYSTR,
                ANYSTR,
                Either("My.Little.Server", "*"),
                "coolNick",
                StrRe("H@?"),
                ANYSTR,  # hopcount
                StrRe("[0-9]"),  # seconds idle
                "0",  # account name
                ANYSTR,  # op level
                "My UniqueReal Name",
            ],
        )

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr("coolNick"), ANYSTR],
        )

    @pytest.mark.parametrize("char", "cuihsnfdlaor")
    @cases.xfailIf(
        lambda self, char: bool(
            char == "l" and self.controller.software_name == "ircu2"
        ),
        "https://github.com/UndernetIRC/ircu2/commit/17c539103abbd0055b2297e17854cd0756c85d62",
    )
    @cases.xfailIf(
        lambda self, char: bool(
            char == "l" and self.controller.software_name == "Nefarious"
        ),
        "https://github.com/evilnet/nefarious2/pull/73",
    )
    def testWhoxOneChar(self, char):
        self._init()
        if "WHOX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("WHOX")

        self.sendLine(2, f"WHO coolNick %{char}")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self.assertMessageMatch(
            reply,
            command=RPL_WHOSPCRPL,
            params=[
                "otherNick",
                StrRe(".+"),
            ],
        )

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr("coolNick"), ANYSTR],
        )

    def testWhoxToken(self):
        """https://github.com/ircv3/ircv3-specifications/pull/482"""
        self._init()
        if "WHOX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("WHOX")

        self.sendLine(2, "WHO coolNick %tn,321")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self.assertMessageMatch(
            reply,
            command=RPL_WHOSPCRPL,
            params=[
                "otherNick",
                "321",
                "coolNick",
            ],
        )

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr("coolNick"), ANYSTR],
        )


@cases.mark_services
class WhoServicesTestCase(BaseWhoTestCase, cases.BaseServerTestCase):
    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("WHOX")
    def testWhoxAccount(self):
        self._init(auth=True)
        if "WHOX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("WHOX")

        self.sendLine(2, "WHO coolNick %na")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self.assertMessageMatch(
            reply,
            command=RPL_WHOSPCRPL,
            params=[
                "otherNick",
                "coolNick",
                "coolAcct",
            ],
        )

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr("coolNick"), ANYSTR],
        )

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("WHOX")
    def testWhoxNoAccount(self):
        self._init(auth=False)
        if "WHOX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("WHOX")

        self.sendLine(2, "WHO coolNick %na")
        messages = self.getMessages(2)

        self.assertEqual(len(messages), 2, "Unexpected number of messages")

        (reply, end) = messages

        self.assertMessageMatch(
            reply,
            command=RPL_WHOSPCRPL,
            params=[
                "otherNick",
                "coolNick",
                "0",
            ],
        )

        self.assertMessageMatch(
            end,
            command=RPL_ENDOFWHO,
            params=["otherNick", InsensitiveStr("coolNick"), ANYSTR],
        )


class WhoInvisibleTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testWhoInvisible(self):
        if self.controller.software_name in ("Bahamut",):
            raise runner.OptionalExtensionNotSupported("WHO mask")

        self.connectClient("evan", name="evan")
        self.sendLine("evan", "MODE evan +i")
        self.getMessages("evan")

        self.connectClient("shivaram", name="shivaram")
        self.getMessages("shivaram")
        self.sendLine("shivaram", "WHO eva*")
        reply_cmds = {msg.command for msg in self.getMessages("shivaram")}
        self.assertEqual(reply_cmds, {RPL_ENDOFWHO})

        # invisibility should not be respected for plain nicknames, only for masks:
        self.sendLine("shivaram", "WHO evan")
        replies = self.getMessages("shivaram")
        reply_cmds = {msg.command for msg in replies}
        self.assertEqual(reply_cmds, {RPL_WHOREPLY, RPL_ENDOFWHO})

        # invisibility should not be respected if the users share a channel
        self.joinChannel("evan", "#test")
        self.joinChannel("shivaram", "#test")
        self.sendLine("shivaram", "WHO eva*")
        replies = self.getMessages("shivaram")
        reply_cmds = {msg.command for msg in replies}
        self.assertEqual(reply_cmds, {RPL_WHOREPLY, RPL_ENDOFWHO})
