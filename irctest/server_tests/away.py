"""
AWAY command (`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-4.1>`__,
`Modern <https://modern.ircdocs.horse/#away-message>`__)
"""

from irctest import cases, runner
from irctest.numerics import (
    RPL_AWAY,
    RPL_NOWAWAY,
    RPL_UNAWAY,
    RPL_USERHOST,
    RPL_WHOISUSER,
)
from irctest.patma import ANYSTR, StrRe


class AwayTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812", "Modern")
    def testAway(self):
        self.connectClient("bar")
        self.getMessages(1)
        self.sendLine(1, "AWAY :I'm not here right now")
        replies = self.getMessages(1)
        self.assertIn(RPL_NOWAWAY, [msg.command for msg in replies])

        self.connectClient("qux")
        self.sendLine(2, "PRIVMSG bar :what's up")
        self.assertMessageMatch(
            self.getMessage(2),
            command=RPL_AWAY,
            params=["qux", "bar", "I'm not here right now"],
        )
        self.getMessages(1)

        self.sendLine(1, "AWAY")
        replies = self.getMessages(1)
        self.assertIn(RPL_UNAWAY, [msg.command for msg in replies])

        self.sendLine(2, "PRIVMSG bar :what's up")
        replies = self.getMessages(2)
        self.assertEqual(len(replies), 0)

    @cases.mark_specifications("Modern")
    def testAwayAck(self):
        """
        "The server acknowledges the change in away status by returning the
        `RPL_NOWAWAY` and `RPL_UNAWAY` numerics."
        -- https://modern.ircdocs.horse/#away-message
        """
        self.connectClient("bar")
        self.sendLine(1, "AWAY :I'm not here right now")
        self.assertMessageMatch(
            self.getMessage(1), command=RPL_NOWAWAY, params=["bar", ANYSTR]
        )
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(1, "AWAY")
        self.assertMessageMatch(
            self.getMessage(1), command=RPL_UNAWAY, params=["bar", ANYSTR]
        )
        self.assertEqual(self.getMessages(1), [])

    @cases.mark_specifications("Modern")
    def testAwayPrivmsg(self):
        """
        "Servers SHOULD notify clients when a user they're interacting with
        is away when relevant"
        -- https://modern.ircdocs.horse/#away-message

        "<client> <nick> :<message>"
        -- https://modern.ircdocs.horse/#rplaway-301
        """
        self.connectClient("bar")
        self.connectClient("qux")

        self.sendLine(2, "PRIVMSG bar :what's up")
        self.assertEqual(self.getMessages(2), [])

        self.sendLine(1, "AWAY :I'm not here right now")
        replies = self.getMessages(1)
        self.assertIn(RPL_NOWAWAY, [msg.command for msg in replies])

        self.sendLine(2, "PRIVMSG bar :what's up")
        self.assertMessageMatch(
            self.getMessage(2),
            command=RPL_AWAY,
            params=["qux", "bar", "I'm not here right now"],
        )

    @cases.mark_specifications("Modern")
    def testAwayWhois(self):
        """
        "Servers SHOULD notify clients when a user they're interacting with
        is away when relevant"
        -- https://modern.ircdocs.horse/#away-message

        "<client> <nick> :<message>"
        -- https://modern.ircdocs.horse/#rplaway-301
        """
        self.connectClient("bar")
        self.connectClient("qux")

        self.sendLine(2, "WHOIS bar")
        msgs = [msg for msg in self.getMessages(2) if msg.command == RPL_AWAY]
        self.assertEqual(
            len(msgs),
            0,
            fail_msg="Expected no RPL_AWAY (301), got: {}",
            extra_format=(msgs,),
        )

        self.sendLine(1, "AWAY :I'm not here right now")
        replies = self.getMessages(1)
        self.assertIn(RPL_NOWAWAY, [msg.command for msg in replies])

        self.sendLine(2, "WHOIS bar")
        msgs = [msg for msg in self.getMessages(2) if msg.command == RPL_AWAY]
        self.assertEqual(
            len(msgs),
            1,
            fail_msg="Expected one RPL_AWAY (301), got: {}",
            extra_format=(msgs,),
        )
        self.assertMessageMatch(
            msgs[0], command=RPL_AWAY, params=["qux", "bar", "I'm not here right now"]
        )

    @cases.mark_specifications("Modern")
    def testAwayUserhost(self):
        """
        "Servers SHOULD notify clients when a user they're interacting with
        is away when relevant"
        -- https://modern.ircdocs.horse/#away-message

        "<client> <nick> :<message>"
        -- https://modern.ircdocs.horse/#rplaway-301
        """
        self.connectClient("bar")

        self.connectClient("qux")
        self.sendLine(2, "USERHOST bar")
        self.assertMessageMatch(
            self.getMessage(2), command=RPL_USERHOST, params=["qux", StrRe(r"bar=\+.*")]
        )

        self.sendLine(1, "AWAY :I'm not here right now")
        replies = self.getMessages(1)
        self.assertIn(RPL_NOWAWAY, [msg.command for msg in replies])

        self.sendLine(2, "USERHOST bar")
        self.assertMessageMatch(
            self.getMessage(2), command=RPL_USERHOST, params=["qux", StrRe(r"bar=-.*")]
        )

    @cases.mark_specifications("Modern")
    def testAwayEmptyMessage(self):
        """
        "If [AWAY] is sent with a nonempty parameter (the 'away message')
        then the user is set to be away. If this command is sent with no
        parameters, or with the empty string as the parameter, the user is no
        longer away."
        -- https://modern.ircdocs.horse/#away-message
        """
        self.connectClient("bar", name="bar")
        self.connectClient("qux", name="qux")

        self.sendLine("bar", "AWAY :I'm not here right now")
        replies = self.getMessages("bar")
        self.assertIn(RPL_NOWAWAY, [msg.command for msg in replies])
        self.sendLine("qux", "WHOIS bar")
        replies = self.getMessages("qux")
        self.assertIn(RPL_WHOISUSER, [msg.command for msg in replies])
        self.assertIn(RPL_AWAY, [msg.command for msg in replies])

        # empty final parameter to AWAY is treated the same as no parameter,
        # i.e., the client is considered to be no longer away
        self.sendLine("bar", "AWAY :")
        replies = self.getMessages("bar")
        self.assertIn(RPL_UNAWAY, [msg.command for msg in replies])
        self.sendLine("qux", "WHOIS bar")
        replies = self.getMessages("qux")
        self.assertIn(RPL_WHOISUSER, [msg.command for msg in replies])
        self.assertNotIn(RPL_AWAY, [msg.command for msg in replies])

    @cases.mark_specifications("Modern")
    @cases.mark_isupport("AWAYLEN")
    def testAwaylen(self):
        """
        "AWAYLEN=<number>
        The AWAYLEN parameter indicates the maximum length for the <reason> of an AWAY command."
        -- https://modern.ircdocs.horse/#awaylen-parameter
        """
        self.connectClient("foo")

        if "AWAYLEN" not in self.server_support:
            raise runner.IsupportTokenNotSupported("AWAYLEN")

        awaylen = int(self.server_support["AWAYLEN"])

        # Set away message at exactly the limit
        valid_away = "a" * awaylen
        self.sendLine(1, f"AWAY :{valid_away}")
        self.assertMessageMatch(
            self.getMessage(1), command="306", params=["foo", ANYSTR]
        )  # RPL_NOWAWAY

        # Set away message longer than the limit
        long_away = "b" * (awaylen + 50)
        self.sendLine(1, f"AWAY :{long_away}")
        self.getMessages(1)

        # Check the away message
        self.connectClient("bar")
        self.sendLine(2, "WHOIS foo")
        msgs = self.getMessages(2)

        away_msgs = [m for m in msgs if m.command == "301"]
        self.assertMessageMatch(
            away_msgs[0], command="301", params=["bar", "foo", ANYSTR]
        )
        self.assertLessEqual(
            len(away_msgs[0].params[2]),
            awaylen,
            f"Server sent away message longer than AWAYLEN {awaylen}",
        )
