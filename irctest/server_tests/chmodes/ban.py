"""
Channel ban (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.3.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.3>`__,
`Modern <https://modern.ircdocs.horse/#ban-channel-mode>`__)
"""

from irctest import cases
from irctest.numerics import ERR_BANNEDFROMCHAN, RPL_BANLIST, RPL_ENDOFBANLIST
from irctest.patma import ANYSTR, StrRe


class BanModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testBan(self):
        """Basic ban operation"""
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
    def testBanList(self):
        """`RPL_BANLIST <https://modern.ircdocs.horse/#rplbanlist-367>`"""
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
