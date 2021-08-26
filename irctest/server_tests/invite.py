import pytest

from irctest import cases
from irctest.numerics import (
    ERR_CHANOPRIVSNEEDED,
    ERR_INVITEONLYCHAN,
    ERR_NOSUCHNICK,
    ERR_NOTONCHANNEL,
    ERR_USERONCHANNEL,
    RPL_INVITING,
)
from irctest.patma import ANYSTR, StrRe


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

    def _testInvite(self, opped, invite_only, modern):
        """
        "Only the user inviting and the user being invited will receive
        notification of the invitation."
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.7

        "      341    RPL_INVITING
              "<channel> <nick>"

         - Returned by the server to indicate that the
           attempted INVITE message was successful and is
           being passed onto the end client."
        -- https://datatracker.ietf.org/doc/html/rfc1459
        -- https://datatracker.ietf.org/doc/html/rfc2812

        "When the invite is successful, the server MUST send a `RPL_INVITING`
        numeric to the command issuer, and an `INVITE` message,
        with the issuer as prefix, to the target user."
        -- https://modern.ircdocs.horse/#invite-message

        "### `RPL_INVITING (341)`

        <client> <nick> <channel>

        Sent as a reply to the [`INVITE`](#invite-message) command to indicate
        that the attempt was successful and the client with the nickname `<nick>`
        has been invited to `<channel>`.
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)

        if invite_only:
            self.sendLine(1, "MODE #chan +i")
            self.assertMessageMatch(
                self.getMessage(1),
                command="MODE",
                params=["#chan", "+i"],
            )

        if not opped:
            self.sendLine(1, "MODE #chan -o foo")
            self.assertMessageMatch(
                self.getMessage(1),
                command="MODE",
                params=["#chan", "-o", "foo"],
            )

        self.sendLine(1, "INVITE bar #chan")
        if modern:
            self.assertMessageMatch(
                self.getMessage(1),
                command=RPL_INVITING,
                params=["foo", "bar", "#chan"],
                fail_msg=f"After “foo” invited “bar” to a channel, “foo” should have "
                f"received “{RPL_INVITING} foo #chan bar” but got this instead: "
                f"{{msg}}",
            )
        else:
            self.assertMessageMatch(
                self.getMessage(1),
                command=RPL_INVITING,
                params=["#chan", "bar"],
                fail_msg=f"After “foo” invited “bar” to a channel, “foo” should have "
                f"received “{RPL_INVITING} #chan bar” but got this instead: {{msg}}",
            )

        messages = self.getMessages(2)
        self.assertNotEqual(
            messages,
            [],
            fail_msg="After using “INVITE #chan bar”, “bar” received nothing.",
        )
        self.assertMessageMatch(
            messages[0],
            prefix=StrRe("foo!.*"),
            command="INVITE",
            params=["bar", "#chan"],
            fail_msg="After “foo” invited “bar”, “bar” should have received "
            "“INVITE bar #chan” but got this instead: {msg}",
        )

    @pytest.mark.parametrize("invite_only", [True, False])
    @cases.mark_specifications("Modern")
    def testInviteModern(self, invite_only):
        self._testInvite(opped=True, invite_only=invite_only, modern=True)

    @pytest.mark.parametrize("invite_only", [True, False])
    @cases.mark_specifications("RFC1459", "RFC2812", deprecated=True)
    def testInviteRfc(self, invite_only):
        self._testInvite(opped=True, invite_only=invite_only, modern=False)

    @cases.mark_specifications("Modern", strict=True)
    def testInviteUnoppedModern(self):
        """Tests invites from unopped users on not-invite-only chans."""
        self._testInvite(opped=False, invite_only=False, modern=True)

    @cases.mark_specifications("RFC1459", "RFC2812", deprecated=True, strict=True)
    def testInviteUnoppedRfc(self, opped, invite_only):
        """Tests invites from unopped users on not-invite-only chans."""
        self._testInvite(opped=False, invite_only=False, modern=False)

    @cases.mark_specifications("RFC2812", "Modern")
    def testInviteNoNotificationForOtherMembers(self):
        """
        "Other channel members are not notified."
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.7

        "Other channel members SHOULD NOT be notified."
        -- https://modern.ircdocs.horse/#invite-message
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.connectClient("baz")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)

        self.sendLine(3, "JOIN #chan")
        self.getMessages(3)

        self.sendLine(1, "INVITE bar #chan")
        self.getMessages(1)

        self.assertEqual(
            self.getMessages(3),
            [],
            fail_msg="After foo used “INVITE #chan bar”, other channel members "
            "were notified: {got}",
        )

    def _testInviteInviteOnly(self, modern):
        """
        "To invite a user to a channel which is invite only (MODE
        +i), the client sending the invite must be recognised as being a
        channel operator on the given channel."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.7

        "When the channel has invite-only
        flag set, only channel operators may issue INVITE command."
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.7

        "When the channel has [invite-only](#invite-only-channel-mode) mode set,
        only channel operators may issue INVITE command.
        Otherwise, the server MUST reject the command with the `ERR_CHANOPRIVSNEEDED`
        numeric."
        -- https://modern.ircdocs.horse/#invite-message
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)

        self.sendLine(1, "MODE #chan +i")
        self.assertMessageMatch(
            self.getMessage(1),
            command="MODE",
            params=["#chan", "+i"],
        )

        self.sendLine(1, "MODE #chan -o foo")
        self.assertMessageMatch(
            self.getMessage(1),
            command="MODE",
            params=["#chan", "-o", "foo"],
        )

        self.sendLine(1, "INVITE bar #chan")
        if modern:
            self.assertMessageMatch(
                self.getMessage(1),
                command=ERR_CHANOPRIVSNEEDED,
                params=["foo", "#chan", ANYSTR],
                fail_msg=f"After “foo” invited “bar” to a channel to an invite-only "
                f"channel without being opped, “foo” should have received "
                f"“{ERR_CHANOPRIVSNEEDED} foo #chan :*” but got this instead: {{msg}}",
            )
        else:
            self.assertMessageMatch(
                self.getMessage(1),
                command=ERR_CHANOPRIVSNEEDED,
                params=["#chan", ANYSTR],
                fail_msg=f"After “foo” invited “bar” to a channel to an invite-only "
                f"channel without being opped, “foo” should have received "
                f"“{ERR_CHANOPRIVSNEEDED} #chan :*” but got this instead: {{msg}}",
            )

    @cases.mark_specifications("Modern")
    def testInviteInviteOnlyModern(self):
        self._testInviteInviteOnly(modern=True)

    @cases.mark_specifications("RFC1459", "RFC2812", deprecated=True)
    def testInviteInviteOnlyRfc(self):
        self._testInviteInviteOnly(modern=False)

    @cases.mark_specifications("RFC2812", "Modern")
    def _testInviteOnlyFromUsersInChannel(self, modern):
        """
        "if the channel exists, only members of the channel are allowed
        to invite other users"
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.7

        "       442    ERR_NOTONCHANNEL
              "<channel> :You're not on that channel"

         - Returned by the server whenever a client tries to
           perform a channel affecting command for which the
           client isn't a member.
        "
        -- https://datatracker.ietf.org/doc/html/rfc2812


        " Only members of the channel are allowed to invite other users.
        Otherwise, the server MUST reject the command with the `ERR_NOTONCHANNEL`
        numeric."
        -- https://modern.ircdocs.horse/#invite-message
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.connectClient("baz")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        # Create the channel
        self.sendLine(3, "JOIN #chan")
        self.getMessages(3)

        self.sendLine(1, "INVITE bar #chan")
        if modern:
            self.assertMessageMatch(
                self.getMessage(1),
                command=ERR_NOTONCHANNEL,
                params=["foo", "#chan", ANYSTR],
                fail_msg=f"After “foo” invited “bar” to a channel it is not on "
                f"#chan, “foo” should have received "
                f"“ERR_NOTONCHANNEL ({ERR_NOTONCHANNEL}) foo #chan :*” but "
                f"got this instead: {{msg}}",
            )
        else:
            self.assertMessageMatch(
                self.getMessage(1),
                command=ERR_NOTONCHANNEL,
                params=["#chan", ANYSTR],
                fail_msg=f"After “foo” invited “bar” to a channel it is not on "
                f"#chan, “foo” should have received "
                f"“ERR_NOTONCHANNEL ({ERR_NOTONCHANNEL}) #chan :*” but "
                f"got this instead: {{msg}}",
            )

        messages = self.getMessages(2)
        self.assertEqual(
            messages,
            [],
            fail_msg="After using “INVITE #chan bar” while the emitter is "
            "not in #chan, “bar” received something.",
        )

    @cases.mark_specifications("Modern")
    def testInviteOnlyFromUsersInChannelModern(self):
        self._testInviteOnlyFromUsersInChannel(modern=True)

    @cases.mark_specifications("RFC2812", deprecated=True)
    def testInviteOnlyFromUsersInChannelRfc(self):
        self._testInviteOnlyFromUsersInChannel(modern=False)

    @cases.mark_specifications("Modern")
    def testInviteAlreadyInChannel(self):
        """
        "If the user is already on the target channel,
        the server MUST reject the command with the `ERR_USERONCHANNEL` numeric."
        -- https://modern.ircdocs.horse/#invite-message
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "JOIN #chan")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, "INVITE bar #chan")

        self.assertMessageMatch(
            self.getMessage(1),
            command=ERR_USERONCHANNEL,
            params=["foo", "bar", "#chan", ANYSTR],
        )
