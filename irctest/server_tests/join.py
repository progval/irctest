"""
The JOIN command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.1>`__,
`Modern <https://modern.ircdocs.horse/#join-message>`__)
"""

from irctest import cases, runner
from irctest.numerics import (
    ERR_BADCHANMASK,
    ERR_FORBIDDENCHANNEL,
    ERR_NOSUCHCHANNEL,
    RPL_ENDOFNAMES,
    RPL_NAMREPLY,
)
from irctest.patma import ANYSTR, StrRe
from irctest.specifications import OptionalBehaviors

ERR_BADCHANNAME = "479"  # Hybrid only, and conflicts with others


JOIN_ERROR_NUMERICS = {
    ERR_BADCHANMASK,
    ERR_NOSUCHCHANNEL,
    ERR_FORBIDDENCHANNEL,
    ERR_BADCHANNAME,
}


class JoinTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812", strict=True)
    def testJoinAllMessages(self):
        """“If a JOIN is successful, the user receives a JOIN message as
        confirmation and is then sent the channel's topic (using RPL_TOPIC) and
        the list of users who are on the channel (using RPL_NAMREPLY), which
        MUST include the user joining.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.1>

        “If a JOIN is successful, the user is then sent the channel's topic
        (using RPL_TOPIC) and the list of users who are on the channel (using
        RPL_NAMREPLY), which must include the user joining.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        """
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        received_commands = {m.command for m in self.getMessages(1)}
        expected_commands = {RPL_NAMREPLY, RPL_ENDOFNAMES, "JOIN"}
        acceptable_commands = expected_commands | {"MODE"}
        self.assertLessEqual(  # set inclusion
            expected_commands,
            received_commands,
            "Server sent {} commands, but at least {} were expected.".format(
                received_commands, expected_commands
            ),
        )
        self.assertLessEqual(  # ditto
            received_commands,
            acceptable_commands,
            "Server sent {} commands, but only {} were expected.".format(
                received_commands, acceptable_commands
            ),
        )

    @cases.xfailIfSoftware(["Bahamut", "irc2"], "trailing space on RPL_NAMREPLY")
    @cases.mark_specifications("RFC2812")
    def testJoinNamreply(self):
        """“353    RPL_NAMREPLY
            "( "=" / "*" / "@" ) <channel>
             :[ "@" / "+" ] <nick> *( " " [ "@" / "+" ] <nick> )”
        -- <https://tools.ietf.org/html/rfc2812#section-5.2>

        This test makes a user join and check what is sent to them.
        """
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")

        for m in self.getMessages(1):
            if m.command == "353":
                self.assertMessageMatch(
                    m, params=["foo", StrRe(r"[=\*@]"), "#chan", StrRe("[@+]?foo")]
                )

        self.connectClient("bar")
        self.sendLine(2, "JOIN #chan")

        for m in self.getMessages(2):
            if m.command == "353":
                self.assertMessageMatch(
                    m,
                    params=[
                        "bar",
                        StrRe(r"[=\*@]"),
                        "#chan",
                        StrRe("([@+]?foo bar|bar [@+]?foo)"),
                    ],
                )

    def testJoinTwice(self):
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan")
        # Note that there may be no message. Both RFCs require replies only
        # if the join is successful, or has an error among the given set.
        for m in self.getMessages(1):
            if m.command == "353":
                self.assertMessageMatch(
                    m, params=["foo", StrRe(r"[=\*@]"), "#chan", StrRe("[@+]?foo")]
                )

    def testJoinPartiallyInvalid(self):
        """TODO: specify this in Modern"""
        self.connectClient("foo")
        if int(self.targmax.get("JOIN") or "4") < 2:
            raise runner.OptionalBehaviorNotSupported(OptionalBehaviors.MULTI_JOIN)

        self.sendLine(1, "JOIN #valid,inv@lid")
        messages = self.getMessages(1)
        received_commands = {m.command for m in messages}
        expected_commands = {RPL_NAMREPLY, RPL_ENDOFNAMES, "JOIN"}
        acceptable_commands = expected_commands | JOIN_ERROR_NUMERICS | {"MODE"}
        self.assertLessEqual(
            expected_commands,
            received_commands,
            "Server sent {} commands, but at least {} were expected.".format(
                received_commands, expected_commands
            ),
        )
        self.assertLessEqual(
            received_commands,
            acceptable_commands,
            "Server sent {} commands, but only {} were expected.".format(
                received_commands, acceptable_commands
            ),
        )

        nb_errors = 0
        for m in messages:
            if m.command in JOIN_ERROR_NUMERICS:
                nb_errors += 1
                self.assertMessageMatch(m, params=["foo", "inv@lid", ANYSTR])

        self.assertEqual(
            nb_errors,
            1,
            fail_msg="Expected 1 error when joining channels '#valid' and 'inv@lid', "
            "got {got}",
        )

    @cases.mark_capabilities("batch", "labeled-response")
    def testJoinPartiallyInvalidLabeledResponse(self):
        """TODO: specify this in Modern"""
        self.connectClient(
            "foo", capabilities=["batch", "labeled-response"], skip_if_cap_nak=True
        )
        if int(self.targmax.get("JOIN") or "4") < 2:
            raise runner.OptionalBehaviorNotSupported(OptionalBehaviors.MULTI_JOIN)

        self.sendLine(1, "@label=label1 JOIN #valid,inv@lid")
        messages = self.getMessages(1)

        first_msg = messages.pop(0)
        last_msg = messages.pop(-1)
        self.assertMessageMatch(
            first_msg, command="BATCH", params=[StrRe(r"\+.*"), "labeled-response"]
        )
        batch_id = first_msg.params[0][1:]
        self.assertMessageMatch(last_msg, command="BATCH", params=["-" + batch_id])

        received_commands = {m.command for m in messages}
        expected_commands = {RPL_NAMREPLY, RPL_ENDOFNAMES, "JOIN"}
        acceptable_commands = expected_commands | JOIN_ERROR_NUMERICS | {"MODE"}
        self.assertLessEqual(
            expected_commands,
            received_commands,
            "Server sent {} commands, but at least {} were expected.".format(
                received_commands, expected_commands
            ),
        )
        self.assertLessEqual(
            received_commands,
            acceptable_commands,
            "Server sent {} commands, but only {} were expected.".format(
                received_commands, acceptable_commands
            ),
        )

        nb_errors = 0
        for m in messages:
            self.assertIn("batch", m.tags)
            self.assertEqual(m.tags["batch"], batch_id)
            if m.command in JOIN_ERROR_NUMERICS:
                nb_errors += 1
                self.assertMessageMatch(m, params=["foo", "inv@lid", ANYSTR])

        self.assertEqual(
            nb_errors,
            1,
            fail_msg="Expected 1 error when joining channels '#valid' and 'inv@lid', "
            "got {got}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testJoinKey(self):
        """Joins a single channel with a key"""
        self.connectClient("chanop")
        self.joinChannel(1, "#chan")
        self.sendLine(1, "MODE #chan +k key")
        self.getMessages(1)

        self.connectClient("joiner")
        self.sendLine(2, "JOIN #chan key")
        self.assertMessageMatch(
            self.getMessage(2),
            command="JOIN",
            params=["#chan"],
        )

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testJoinKeys(self):
        """Joins two channels, both with keys"""
        self.connectClient("chanop")
        if self.targmax.get("JOIN", "1000") == "1":
            raise runner.OptionalBehaviorNotSupported(OptionalBehaviors.MULTI_JOIN)
        self.joinChannel(1, "#chan1")
        self.sendLine(1, "MODE #chan1 +k key1")
        self.getMessages(1)
        self.joinChannel(1, "#chan2")
        self.sendLine(1, "MODE #chan2 +k key2")
        self.getMessages(1)

        self.connectClient("joiner")
        self.sendLine(2, "JOIN #chan1,#chan2 key1,key2")
        self.assertMessageMatch(
            self.getMessage(2),
            command="JOIN",
            params=["#chan1"],
        )
        self.assertMessageMatch(
            [
                msg
                for msg in self.getMessages(2)
                if msg.command not in {RPL_NAMREPLY, RPL_ENDOFNAMES}
            ][0],
            command="JOIN",
            params=["#chan2"],
        )

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testJoinManySingleKey(self):
        """Joins two channels, the first one has a key."""
        self.connectClient("chanop")
        if self.targmax.get("JOIN", "1000") == "1":
            raise runner.OptionalBehaviorNotSupported(OptionalBehaviors.MULTI_JOIN)
        self.joinChannel(1, "#chan1")
        self.sendLine(1, "MODE #chan1 +k key1")
        self.getMessages(1)
        self.joinChannel(1, "#chan2")
        self.getMessages(1)

        self.connectClient("joiner")
        self.sendLine(2, "JOIN #chan1,#chan2 key1")
        self.assertMessageMatch(
            self.getMessage(2),
            command="JOIN",
            params=["#chan1"],
        )
        self.assertMessageMatch(
            [
                msg
                for msg in self.getMessages(2)
                if msg.command not in {RPL_NAMREPLY, RPL_ENDOFNAMES}
            ][0],
            command="JOIN",
            params=["#chan2"],
        )
