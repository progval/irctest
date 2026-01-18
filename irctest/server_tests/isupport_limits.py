"""
Tests for ISUPPORT limit enforcement (`Modern
<https://modern.ircdocs.horse/#rplisupport-parameters>`__)
"""

import pytest

from irctest import cases, runner
from irctest.numerics import (
    ERR_ERRONEUSNICKNAME,
    ERR_FORBIDDENCHANNEL,
    ERR_NOSUCHCHANNEL,
    ERR_TOOMANYCHANNELS,
)
from irctest.patma import ANYSTR, Either

ERR_BADCHANNAME = "479"  # Hybrid only, and conflicts with others


class IsupportLimitTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    @cases.mark_isupport("CHANLIMIT")
    @pytest.mark.parametrize("prefix", ["#", "&"])
    def testChanlimit(self, prefix):
        """
        "CHANLIMIT=<prefixes>:[limit]{,<prefixes>:[limit]}"
        -- https://modern.ircdocs.horse/#chanlimit-parameter
        """
        self.connectClient("foo")

        if "CHANLIMIT" not in self.server_support:
            raise runner.IsupportTokenNotSupported("CHANLIMIT")

        pairs = [
            part.split(":", 1) for part in self.server_support["CHANLIMIT"].split(",")
        ]
        limits = {pair[0]: int(pair[1]) if pair[1] else None for pair in pairs}

        self.assertTrue(limits, "CHANLIMIT is empty")

        limit = limits.get(prefix)
        if limit is None:
            raise runner.ImplementationChoice(f"No limit for {prefix} channels")

        # Join up to the limit
        for i in range(limit):
            self.sendLine(1, f"JOIN {prefix}chan{i}")
            self.assertMessageMatch(
                self.getMessage(1),
                command="JOIN",
                params=[f"{prefix}chan{i}"],
                fail_msg=f"Failed to join channel {i + 1}/{limit}",
            )
            self.getMessages(1)  # clear any remaining messages

        # Try to join one more - should fail
        self.sendLine(1, f"JOIN {prefix}chan")
        self.assertMessageMatch(
            self.getMessage(1),
            command=ERR_TOOMANYCHANNELS,
            params=["foo", f"{prefix}chan", ANYSTR],
        )

    @cases.mark_specifications("Modern")
    @cases.mark_isupport("CHANNELLEN")
    @pytest.mark.parametrize("prefix", ["#", "&"])
    def testChannellen(self, prefix):
        """
        "CHANNELLEN=<number>
        The CHANNELLEN parameter specifies the maximum length of a channel name that a client may join."
        -- https://modern.ircdocs.horse/#channellen-parameter
        """
        self.connectClient("foo")

        if "CHANNELLEN" not in self.server_support:
            raise runner.IsupportTokenNotSupported("CHANNELLEN")

        chantypes = self.server_support.get("CHANTYPES", "#")
        if prefix not in chantypes:
            raise runner.NotImplementedByController(
                f"Server does not support {prefix} channels"
            )

        channellen = int(self.server_support["CHANNELLEN"])

        # Try a channel name at exactly the limit
        valid_chan = prefix + "a" * (channellen - 1)
        self.sendLine(1, f"JOIN {valid_chan}")
        self.assertMessageMatch(self.getMessage(1), command="JOIN", params=[valid_chan])

        # Try a channel name longer than the limit
        self.getMessages(1)  # clear
        invalid_chan = prefix + "b" * channellen
        self.sendLine(1, f"JOIN {invalid_chan}")
        self.assertMessageMatch(
            self.getMessage(1),
            command=Either(ERR_NOSUCHCHANNEL, ERR_BADCHANNAME, ERR_FORBIDDENCHANNEL),
            params=["foo", invalid_chan, ANYSTR],
        )

    @cases.mark_specifications("Modern")
    @cases.mark_isupport("NICKLEN")
    def testNicklen(self):
        """
        "NICKLEN=<number>
        "The NICKLEN parameter indicates the maximum length of a nickname that a client may set.
        Clients on the network MAY have longer nicks than this.
        The value MUST be specified and MUST be a positive integer.
        30 or 31 are typical values for this parameter advertised by servers today."
        -- https://modern.ircdocs.horse/#nicklen-parameter
        """
        self.connectClient("foo")

        if "NICKLEN" not in self.server_support:
            raise runner.IsupportTokenNotSupported("NICKLEN")

        nicklen = int(self.server_support["NICKLEN"])

        # Try a nick at exactly the limit
        valid_nick = "a" * nicklen
        self.sendLine(1, f"NICK {valid_nick}")
        self.assertMessageMatch(self.getMessage(1), command="NICK", params=[valid_nick])

        # Try a nick longer than the limit
        invalid_nick = "b" * (nicklen + 5)
        self.sendLine(1, f"NICK {invalid_nick}")
        self.assertMessageMatch(
            self.getMessage(1),
            command=ERR_ERRONEUSNICKNAME,
            params=[valid_nick, invalid_nick, ANYSTR],
        )
