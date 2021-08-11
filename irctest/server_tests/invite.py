from irctest import cases
from irctest.numerics import ERR_INVITEONLYCHAN, ERR_NOSUCHNICK, RPL_INVITING


class InviteTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testInvites(self):
        """Test some basic functionality related to INVITE and the +i mode.

        https://modern.ircdocs.horse/#invite-only-channel-mode
        https://modern.ircdocs.horse/#rplinviting-341
        """
        self.connectClient("foo")
        self.joinChannel(1, "#chan")
        self.sendLine(1, "MODE #chan +i")
        self.getMessages(1)
        self.sendLine(1, "INVITE bar #chan")
        m = self.getMessage(1)
        self.assertEqual(m.command, ERR_NOSUCHNICK)

        self.connectClient("bar")
        self.sendLine(2, "JOIN #chan")
        m = self.getMessage(2)
        self.assertEqual(m.command, ERR_INVITEONLYCHAN)

        self.sendLine(1, "INVITE bar #chan")
        m = self.getMessage(1)
        # modern/ircv3 param order: inviter, invitee, channel
        self.assertMessageMatch(m, command=RPL_INVITING, params=["foo", "bar", "#chan"])
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="INVITE", params=["bar", "#chan"])
        self.assertTrue(m.prefix.startswith("foo"))  # nickmask of inviter

        # we were invited, so join should succeed now
        self.joinChannel(2, "#chan")

    @cases.mark_specifications("RFC1459", "RFC2812", deprecated=True)
    def testInviteNonExistingChannelTransmitted(self):
        """“There is no requirement that the channel the target user is being
        invited to must exist or be a valid channel.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.7>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.7>

        “Only the user inviting and the user being invited will receive
        notification of the invitation.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.7>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.getMessages(2)
        self.sendLine(1, "INVITE #chan bar")
        self.getMessages(1)
        messages = self.getMessages(2)
        self.assertNotEqual(
            messages,
            [],
            fail_msg="After using “INVITE #chan bar” while #chan does "
            "not exist, “bar” received nothing.",
        )
        self.assertMessageMatch(
            messages[0],
            command="INVITE",
            params=["#chan", "bar"],
            fail_msg="After “foo” invited “bar” do non-existing channel "
            "#chan, “bar” should have received “INVITE #chan bar” but "
            "got this instead: {msg}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812", deprecated=True)
    def testInviteNonExistingChannelEchoed(self):
        """“There is no requirement that the channel the target user is being
        invited to must exist or be a valid channel.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.7>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.7>

        “Only the user inviting and the user being invited will receive
        notification of the invitation.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.7>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.getMessages(2)
        self.sendLine(1, "INVITE #chan bar")
        messages = self.getMessages(1)
        self.assertNotEqual(
            messages,
            [],
            fail_msg="After using “INVITE #chan bar” while #chan does "
            "not exist, the author received nothing.",
        )
        self.assertMessageMatch(
            messages[0],
            command="INVITE",
            params=["#chan", "bar"],
            fail_msg="After “foo” invited “bar” do non-existing channel "
            "#chan, “foo” should have received “INVITE #chan bar” but "
            "got this instead: {msg}",
        )
