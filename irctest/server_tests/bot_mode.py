"""
`IRCv3 bot mode <https://ircv3.net/specs/extensions/bot-mode>`_
"""

from irctest import cases, runner
from irctest.numerics import RPL_WHOISBOT
from irctest.patma import ANYDICT, ANYSTR, StrRe
from irctest.specifications import IsupportTokens


@cases.mark_specifications("IRCv3")
@cases.mark_isupport("BOT")
class BotModeTestCase(cases.BaseServerTestCase):
    def setUp(self):
        super().setUp()
        self.connectClient("modegettr")
        if "BOT" not in self.server_support:
            raise runner.IsupportTokenNotSupported(IsupportTokens.BOT)
        self._mode_char = self.server_support["BOT"]

    def _initBot(self):
        self.assertEqual(
            len(self._mode_char),
            1,
            fail_msg=(
                f"BOT ISUPPORT token should be exactly one character, "
                f"but is: {self._mode_char!r}"
            ),
        )

        self.connectClient("botnick", "bot")

        self.sendLine("bot", f"MODE botnick +{self._mode_char}")

        # Check echoed mode
        while True:
            msg = self.getMessage("bot")
            if msg.command != "NOTICE":
                # Unreal sends the BOTMOTD here
                self.assertMessageMatch(
                    msg,
                    command="MODE",
                    params=["botnick", StrRe(r"\+?" + self._mode_char)],
                )
                break

    def testBotMode(self):
        self._initBot()

    def testBotWhois(self):
        self._initBot()

        self.connectClient("usernick", "user")
        self.sendLine("user", "WHOIS botnick")
        messages = self.getMessages("user")
        messages = [msg for msg in messages if msg.command == RPL_WHOISBOT]
        self.assertEqual(
            len(messages),
            1,
            msg=(
                f"Expected exactly one RPL_WHOISBOT ({RPL_WHOISBOT}), "
                f"got: {messages}"
            ),
        )

        (message,) = messages
        self.assertMessageMatch(
            message, command=RPL_WHOISBOT, params=["usernick", "botnick", ANYSTR]
        )

    @cases.xfailIfSoftware(
        ["InspIRCd"],
        "Uses only vendor tags for now: https://github.com/inspircd/inspircd/pull/1910",
    )
    def testBotPrivateMessage(self):
        self._initBot()

        self.connectClient(
            "usernick", "user", capabilities=["message-tags"], skip_if_cap_nak=True
        )

        self.sendLine("bot", "PRIVMSG usernick :beep boop")
        self.getMessages("bot")  # Synchronizes

        self.assertMessageMatch(
            self.getMessage("user"),
            command="PRIVMSG",
            params=["usernick", "beep boop"],
            tags={StrRe("(draft/)?bot"): None, **ANYDICT},
        )

    @cases.xfailIfSoftware(
        ["InspIRCd"],
        "Uses only vendor tags for now: https://github.com/inspircd/inspircd/pull/1910",
    )
    def testBotChannelMessage(self):
        self._initBot()

        self.connectClient(
            "usernick", "user", capabilities=["message-tags"], skip_if_cap_nak=True
        )

        self.sendLine("bot", "JOIN #chan")
        self.sendLine("user", "JOIN #chan")
        self.getMessages("bot")
        self.getMessages("user")

        self.sendLine("bot", "PRIVMSG #chan :beep boop")
        self.getMessages("bot")  # Synchronizes

        self.assertMessageMatch(
            self.getMessage("user"),
            command="PRIVMSG",
            params=["#chan", "beep boop"],
            tags={StrRe("(draft/)?bot"): None, **ANYDICT},
        )

    def testBotWhox(self):
        self._initBot()

        self.connectClient(
            "usernick", "user", capabilities=["message-tags"], skip_if_cap_nak=True
        )

        self.sendLine("bot", "JOIN #chan")
        self.sendLine("user", "JOIN #chan")
        self.getMessages("bot")
        self.getMessages("user")

        self.sendLine("user", "WHO #chan")
        msg1 = self.getMessage("user")
        self.assertMessageMatch(
            msg1, command="352", fail_msg="Expected WHO response (352), got: {msg}"
        )
        msg2 = self.getMessage("user")
        self.assertMessageMatch(
            msg2, command="352", fail_msg="Expected WHO response (352), got: {msg}"
        )

        if msg1.params[5] == "botnick":
            msg = msg1
        elif msg2.params[5] == "botnick":
            msg = msg2
        else:
            assert False, "No WHO response contained botnick"

        self.assertMessageMatch(
            msg,
            command="352",
            params=[
                "usernick",
                "#chan",
                ANYSTR,  # ident
                ANYSTR,  # hostname
                ANYSTR,  # server
                "botnick",
                StrRe(f".*{self._mode_char}.*"),
                ANYSTR,  # realname
            ],
            fail_msg="Expected WHO response with bot flag, got: {msg}",
        )
