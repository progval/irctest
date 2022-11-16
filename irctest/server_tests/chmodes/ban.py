"""
Channel ban (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.3.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.3>`__,
`Modern <https://modern.ircdocs.horse/#ban-channel-mode>`__)
and ban exception (`Modern <https://modern.ircdocs.horse/#exception-channel-mode>`__)
"""

from irctest import cases, runner
from irctest.numerics import (
    ERR_BANNEDFROMCHAN,
    ERR_CANNOTSENDTOCHAN,
    RPL_BANLIST,
    RPL_ENDOFBANLIST,
)
from irctest.patma import ANYSTR, StrRe


class BanModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testBanJoin(self):
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.connectClient("Bar", name="bar")
        self.getMessages("bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_BANNEDFROMCHAN)

        self.sendLine("chanop", "MODE #chan -b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")

    @cases.mark_specifications("Modern")
    def testBanPrivmsg(self):
        """
        TODO: this checks the following quote is false:

        "If `<target>` is a channel name and the client is [banned](#ban-channel-mode)
        and not covered by a [ban exception](#ban-exception-channel-mode), the
        message will not be delivered and the command will silently fail."
        -- https://modern.ircdocs.horse/#privmsg-message

        to check https://github.com/ircdocs/modern-irc/pull/201
        """
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.connectClient("Bar", name="bar")
        self.getMessages("bar")
        self.sendLine("bar", "JOIN #chan")
        self.getMessages("bar")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")
        self.getMessages("chanop")
        self.getMessages("bar")

        self.sendLine("bar", "PRIVMSG #chan :hello world")
        self.assertMessageMatch(
            self.getMessage("bar"),
            command=ERR_CANNOTSENDTOCHAN,
            params=["Bar", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("bar"), [])
        self.assertEqual(self.getMessages("chanop"), [])

        self.sendLine("chanop", "MODE #chan -b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")
        self.getMessages("chanop")
        self.getMessages("bar")

        self.sendLine("bar", "PRIVMSG #chan :hello again")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="PRIVMSG",
            params=["#chan", "hello again"],
        )
        self.assertEqual(self.getMessages("bar"), [])

    @cases.mark_specifications("Modern")
    def testBanList(self):
        """`RPL_BANLIST <https://modern.ircdocs.horse/#rplbanlist-367>`_"""
        self.connectClient("chanop")
        self.joinChannel(1, "#chan")
        self.getMessages(1)
        self.sendLine(1, "MODE #chan +b bar!*@*")
        self.assertMessageMatch(self.getMessage(1), command="MODE")

        self.sendLine(1, "MODE #chan +b")

        m = self.getMessage(1)
        if len(m.params) == 3:
            # Old format
            self.assertMessageMatch(
                m,
                command=RPL_BANLIST,
                params=[
                    "chanop",
                    "#chan",
                    "bar!*@*",
                ],
            )
        else:
            self.assertMessageMatch(
                m,
                command=RPL_BANLIST,
                params=[
                    "chanop",
                    "#chan",
                    "bar!*@*",
                    StrRe("chanop(!.*@.*)?"),
                    StrRe("[0-9]+"),
                ],
            )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFBANLIST,
            params=[
                "chanop",
                "#chan",
                ANYSTR,
            ],
        )

    @cases.mark_specifications("Modern")
    def testBanException(self):
        """`Exception mode <https://modern.ircdocs.horse/#exception-channel-mode`_,
        detected using `ISUPPORT EXCEPTS
        <https://modern.ircdocs.horse/#excepts-parameter>`_ and checked against
        `ISUPPORT CHANMODES <https://modern.ircdocs.horse/#chanmodes-parameter>`_"""
        self.connectClient("chanop", name="chanop")

        if "EXCEPTS" in self.server_support:
            mode = self.server_support["EXCEPTS"] or "e"
            if "CHANMODES" in self.server_support:
                self.assertIn(
                    mode,
                    self.server_support["CHANMODES"],
                    fail_msg="ISUPPORT EXCEPTS is present, but '{item}' is missing "
                    "from 'CHANMODES={list}'",
                )
                self.assertIn(
                    mode,
                    self.server_support["CHANMODES"].split(",")[0],
                    fail_msg="ISUPPORT EXCEPTS is present, but '{item}' is not "
                    "in group A",
                )
        else:
            mode = "e"
            if "CHANMODES" in self.server_support:
                if "e" not in self.server_support["CHANMODES"]:
                    raise runner.OptionalExtensionNotSupported(
                        "Ban exception (or mode letter is not +e)"
                    )
                self.assertIn(
                    mode,
                    self.server_support["CHANMODES"].split(",")[0],
                    fail_msg="Mode +e (assumed to be ban exception) is present, "
                    "but 'e' is not in group A",
                )
            else:
                raise runner.OptionalExtensionNotSupported("ISUPPORT CHANMODES")

        self.sendLine("chanop", "JOIN #chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +b ba*!*@*")
        self.getMessages("chanop")

        # banned client cannot join
        self.connectClient("Bar", name="bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_BANNEDFROMCHAN)

        # chanop sets exception
        self.sendLine("chanop", "MODE #chan +e *ar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        # client can now join
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")

    # TODO: Add testBanExceptionList, once the numerics are specified in Modern

    @cases.mark_specifications("Ergo")
    def testCaseInsensitive(self):
        """Some clients allow unsetting modes if their argument matches
        up to normalization"""
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +b BAR!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.connectClient("Bar", name="bar")
        self.getMessages("bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_BANNEDFROMCHAN)

        self.sendLine("chanop", "MODE #chan -b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")
