"""
User limit channel mode (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.3.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.3>`__,
`Modern <https://modern.ircdocs.horse/#client-limit-channel-mode>`__)
"""

import pytest

from irctest import cases
from irctest.numerics import ERR_CHANNELISFULL, ERR_INVALIDMODEPARAM
from irctest.patma import ANYSTR
from irctest.exceptions import NoMessageException


class LimitTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testLimitMode(self):
        # Create channel and set limit to 2 users
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +l 2")
        self.assertMessageMatch(
            self.getMessage("chanop"), command="MODE", params=["#chan", "+l", "2"]
        )

        # Second user should be able to join
        self.connectClient("user2", name="user2")
        self.joinChannel("user2", "#chan")
        self.getMessages("chanop")
        self.getMessages("user2")

        # Third user should not be able to join (limit reached)
        self.connectClient("user3", name="user3")
        self.sendLine("user3", "JOIN #chan")
        self.assertMessageMatch(
            self.getMessage("user3"),
            command=ERR_CHANNELISFULL,
            params=["user3", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("user3"), [])

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testLimitRemoval(self):
        # Create channel and set limit to 1 user
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +l 1")
        self.getMessages("chanop")

        # Verify second user can't join
        self.connectClient("user2", name="user2")
        self.sendLine("user2", "JOIN #chan")
        self.assertMessageMatch(
            self.getMessage("user2"),
            command=ERR_CHANNELISFULL,
            params=["user2", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("user2"), [])

        # Remove the limit
        self.sendLine("chanop", "MODE #chan -l")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE", params=["#chan", "-l"])

        # Now user2 should be able to join
        self.joinChannel("user2", "#chan")

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testLimitChange(self):
        # Create channel with two users
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.connectClient("user2", name="user2")
        self.joinChannel("user2", "#chan")
        self.getMessages("chanop")
        self.getMessages("user2")

        # Set limit to 2 (current number of users)
        self.sendLine("chanop", "MODE #chan +l 2")
        self.getMessages("chanop")

        # Third user can't join
        self.connectClient("user3", name="user3")
        self.sendLine("user3", "JOIN #chan")
        self.assertMessageMatch(
            self.getMessage("user3"),
            command=ERR_CHANNELISFULL,
            params=["user3", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("user3"), [])

        # Increase limit to 3
        self.sendLine("chanop", "MODE #chan +l 3")
        self.assertMessageMatch(
            self.getMessage("chanop"), command="MODE", params=["#chan", "+l", "3"]
        )

        # Now user3 should be able to join
        self.joinChannel("user3", "#chan")

    @cases.mark_specifications("Modern")
    def testLimitDecrease(self):
        # Create channel with three users
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.connectClient("user2", name="user2")
        self.joinChannel("user2", "#chan")
        self.getMessages("chanop")
        self.getMessages("user2")

        self.connectClient("user3", name="user3")
        self.joinChannel("user3", "#chan")
        self.getMessages("chanop")
        self.getMessages("user2")
        self.getMessages("user3")

        # Set limit to 1 (less than current number of users)
        self.sendLine("chanop", "MODE #chan +l 1")
        self.getMessages("chanop")
        self.getMessages("user2")
        self.getMessages("user3")

        # All users should still be in the channel and able to send messages
        self.sendLine("user2", "PRIVMSG #chan :still here")
        self.getMessages("user2")

        self.assertMessageMatch(
            self.getMessage("chanop"), command="PRIVMSG", params=["#chan", "still here"]
        )
        self.assertMessageMatch(
            self.getMessage("user3"), command="PRIVMSG", params=["#chan", "still here"]
        )

        # But a fourth user can't join
        self.connectClient("user4", name="user4")
        self.sendLine("user4", "JOIN #chan")
        self.assertMessageMatch(
            self.getMessage("user4"),
            command=ERR_CHANNELISFULL,
            params=["user4", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("user4"), [])

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testLimitAfterPart(self):
        # Create channel and set limit to 2
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +l 2")
        self.getMessages("chanop")

        # Second user joins
        self.connectClient("user2", name="user2")
        self.joinChannel("user2", "#chan")
        self.getMessages("chanop")
        self.getMessages("user2")

        # Third user can't join
        self.connectClient("user3", name="user3")
        self.sendLine("user3", "JOIN #chan")
        self.assertMessageMatch(
            self.getMessage("user3"),
            command=ERR_CHANNELISFULL,
            params=["user3", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("user3"), [])

        # user2 parts
        self.sendLine("user2", "PART #chan")
        self.getMessages("chanop")
        self.getMessages("user2")

        # Now user3 should be able to join
        self.joinChannel("user3", "#chan")

    @pytest.mark.parametrize(
        "limit",
        ["0", "-1", "abc", ""],
        ids=["zero", "negative", "non-numeric", "empty"],
    )
    @cases.mark_specifications("Modern")
    def testLimitInvalidValues(self, limit):
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", f"MODE #chan +l :{limit}")
        try:
            reply = self.getMessage("chanop")
        except NoMessageException:
            # Mode was silently ignored. Verify by trying to join with extra users
            self.connectClient("user2", name="user2")
            self.joinChannel("user2", "#chan")
            self.connectClient("user3", name="user3")
            self.joinChannel("user3", "#chan")
        else:
            # If there's a reply, it should be ERR_INVALIDMODEPARAM
            self.assertMessageMatch(
                reply,
                command=ERR_INVALIDMODEPARAM,
                params=["chanop", "#chan", "l", ANYSTR, ANYSTR],
            )

            # Mode was rejected, so users can still join
            self.connectClient("user2", name="user2")
            self.joinChannel("user2", "#chan")
            self.connectClient("user3", name="user3")
            self.joinChannel("user3", "#chan")

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testLimitMultipleChannels(self):
        # Create two channels
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan1")
        self.getMessages("chanop")
        self.joinChannel("chanop", "#chan2")
        self.getMessages("chanop")

        # Set limit only on #chan1
        self.sendLine("chanop", "MODE #chan1 +l 1")
        self.getMessages("chanop")

        # User should be blocked from #chan1 but not #chan2
        self.connectClient("user", name="user")

        self.sendLine("user", "JOIN #chan1")
        self.assertMessageMatch(
            self.getMessage("user"),
            command=ERR_CHANNELISFULL,
            params=["user", "#chan1", ANYSTR],
        )
        self.assertEqual(self.getMessages("user"), [])

        # But can join #chan2
        self.joinChannel("user", "#chan2")

    @cases.mark_specifications("Modern")
    def testLimitWithInvite(self):
        """Test that invited users can bypass the channel limit.

        "An INVITE message can be used by channel members to allow a user
        to join despite the limit."
        -- https://modern.ircdocs.horse/#client-limit-channel-mode
        """
        # Create channel and set limit to 1
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +l 1")
        self.getMessages("chanop")

        # Second user can't join (limit reached)
        self.connectClient("user2", name="user2")
        self.sendLine("user2", "JOIN #chan")
        self.assertMessageMatch(
            self.getMessage("user2"),
            command=ERR_CHANNELISFULL,
            params=["user2", "#chan", ANYSTR],
        )
        self.assertEqual(self.getMessages("user2"), [])

        # Invite the user
        self.sendLine("chanop", "INVITE user2 #chan")
        self.getMessages("chanop")
        self.getMessages("user2")

        # Can now join #chan despite the limi despite the limitt
        self.sendLine("user2", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("user2"), command="JOIN", params=["#chan"])
