"""
`IRCv3 away-notify <https://ircv3.net/specs/extensions/away-notify>`_
"""

from irctest import cases
from irctest.numerics import RPL_NOWAWAY, RPL_UNAWAY
from irctest.patma import ANYSTR, StrRe


class AwayNotifyTestCase(cases.BaseServerTestCase):
    @cases.mark_capabilities("away-notify")
    def testAwayNotify(self):
        """Basic away-notify test."""
        self.connectClient("foo", capabilities=["away-notify"], skip_if_cap_nak=True)
        self.getMessages(1)
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.getMessages(2)
        self.joinChannel(2, "#chan")
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(2, "AWAY :i'm going away")
        self.assertMessageMatch(
            self.getMessage(2), command=RPL_NOWAWAY, params=["bar", ANYSTR]
        )
        self.assertEqual(self.getMessages(2), [])

        awayNotify = self.getMessage(1)
        self.assertMessageMatch(
            awayNotify,
            prefix=StrRe("bar!.*"),
            command="AWAY",
            params=["i'm going away"],
        )

        self.sendLine(2, "AWAY")
        self.assertMessageMatch(
            self.getMessage(2), command=RPL_UNAWAY, params=["bar", ANYSTR]
        )
        self.assertEqual(self.getMessages(2), [])

        awayNotify = self.getMessage(1)
        self.assertMessageMatch(
            awayNotify, prefix=StrRe("bar!.*"), command="AWAY", params=[]
        )

    @cases.mark_capabilities("away-notify")
    def testAwayNotifyOnJoin(self):
        """The away-notify specification states:
        "Clients will be sent an AWAY message [...] when a user joins
        and has an away message set."
        """
        self.connectClient("foo", capabilities=["away-notify"], skip_if_cap_nak=True)
        self.getMessages(1)
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.getMessages(2)
        self.sendLine(2, "AWAY :i'm already away")
        self.getMessages(2)

        self.joinChannel(2, "#chan")
        self.assertNotIn(
            "AWAY",
            [m.command for m in self.getMessages(2)],
            "joining user got their own away status when they joined",
        )

        messages = [msg for msg in self.getMessages(1) if msg.command == "AWAY"]
        self.assertEqual(
            len(messages),
            1,
            "Someone away joined a channel, "
            "but users in the channel did not get AWAY messages.",
        )
        awayNotify = messages[0]
        self.assertMessageMatch(awayNotify, command="AWAY", params=["i'm already away"])
        self.assertTrue(
            awayNotify.prefix.startswith("bar!"),
            "Unexpected away-notify source: %s" % (awayNotify.prefix,),
        )
