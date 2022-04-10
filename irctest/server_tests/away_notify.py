"""
`IRCv3 away-notify <https://ircv3.net/specs/extensions/away-notify>`_
"""

from irctest import cases


class AwayNotifyTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
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
        self.getMessages(2)

        awayNotify = self.getMessage(1)
        self.assertMessageMatch(awayNotify, command="AWAY", params=["i'm going away"])
        self.assertTrue(
            awayNotify.prefix.startswith("bar!"),
            "Unexpected away-notify source: %s" % (awayNotify.prefix,),
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
        self.getMessages(2)

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
