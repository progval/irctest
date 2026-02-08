"""
Invite exception mode (`Modern
<https://modern.ircdocs.horse/#invite-exception-channel-mode>`__)

The invite exception mode allows channel operators to specify masks of users
who can join an invite-only channel without needing an explicit INVITE.
"""

from irctest import cases, runner
from irctest.numerics import ERR_INVITEONLYCHAN, RPL_ENDOFINVEXLIST, RPL_INVEXLIST
from irctest.patma import ANYSTR, StrRe
from irctest.specifications import OptionalBehaviors


@cases.mark_isupport("INVEX")
class InviteExceptionTestCase(cases.BaseServerTestCase):
    def getInviteExceptionMode(self) -> str:
        """Get the invite exception mode letter from ISUPPORT and validate it."""
        if self.server_support and "INVEX" in self.server_support:
            mode = self.server_support["INVEX"] or "I"
            if "CHANMODES" in self.server_support:
                chanmodes = self.server_support["CHANMODES"]
                if chanmodes:
                    self.assertIn(
                        mode,
                        chanmodes,
                        fail_msg="ISUPPORT INVEX is present, but '{item}' is missing "
                        "from 'CHANMODES={list}'",
                    )
                    self.assertIn(
                        mode,
                        chanmodes.split(",")[0],
                        fail_msg="ISUPPORT INVEX is present, but '{item}' is not "
                        "in group A",
                    )
        else:
            mode = "I"
            if self.server_support and "CHANMODES" in self.server_support:
                chanmodes = self.server_support["CHANMODES"]
                if chanmodes and "I" not in chanmodes:
                    raise runner.OptionalBehaviorNotSupported(
                        OptionalBehaviors.INVITE_EXCEPTION_MODE,
                    )
                if chanmodes:
                    self.assertIn(
                        mode,
                        chanmodes.split(",")[0],
                        fail_msg="Mode +I (assumed to be invite exception) is present, "
                        "but 'I' is not in group A",
                    )
            else:
                raise runner.OptionalBehaviorNotSupported(
                    OptionalBehaviors.INVITE_EXCEPTION_MODE,
                )
        return mode

    @cases.mark_specifications("Modern")
    def testInviteException(self):
        """Test that invite exception (+I) allows users to bypass invite-only (+i).

        https://modern.ircdocs.horse/#invite-exception-channel-mode
        """
        self.connectClient("chanop", name="chanop")
        mode = self.getInviteExceptionMode()

        # Create channel and set invite-only mode
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +i")
        self.getMessages("chanop")

        # User matching no exception should be blocked
        self.connectClient("Bar", name="bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_INVITEONLYCHAN)

        # Set invite exception for bar!*@*
        self.sendLine("chanop", f"MODE #chan +{mode} bar!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"+{mode}", "bar!*@*"],
        )

        # User matching the exception should now be able to join
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")

    @cases.mark_specifications("Modern")
    def testInviteExceptionList(self):
        """Test querying the invite exception list.

        "346    RPL_INVEXLIST
                "<client> <channel> <mask>"

        Sent as a reply to the MODE command, when clients are viewing the current
        entries on a channel’s invite-exception list. "
        -- https://modern.ircdocs.horse/#rplinvexlist-346

        "347    RPL_ENDOFINVEXLIST
                "<client> <channel> :End of Channel Invite Exception List"

        Sent as a reply to the MODE command, this numeric indicates the end of
        a channel’s invite-exception list."
        -- https://modern.ircdocs.horse/#rplendofinvexlist-347

        Note: Some servers include optional [<who> <set-ts>] parameters
        like RPL_BANLIST does.
        """
        self.connectClient("chanop", name="chanop")
        mode = self.getInviteExceptionMode()

        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        # Set an invite exception
        self.sendLine("chanop", f"MODE #chan +{mode} bar!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"+{mode}", "bar!*@*"],
        )

        # Query the invite exception list
        self.sendLine("chanop", f"MODE #chan +{mode}")

        m = self.getMessage("chanop")
        if len(m.params) == 3:
            # Old format
            self.assertMessageMatch(
                m,
                command=RPL_INVEXLIST,
                params=[
                    "chanop",
                    "#chan",
                    "bar!*@*",
                ],
            )
        else:
            # Modern format with who set it and timestamp
            self.assertMessageMatch(
                m,
                command=RPL_INVEXLIST,
                params=[
                    "chanop",
                    "#chan",
                    "bar!*@*",
                    StrRe("chanop(!.*@.*)?"),
                    StrRe("[0-9]+"),
                ],
            )

        self.assertMessageMatch(
            self.getMessage("chanop"),
            command=RPL_ENDOFINVEXLIST,
            params=[
                "chanop",
                "#chan",
                ANYSTR,
            ],
        )

    @cases.mark_specifications("Modern")
    def testInviteExceptionRemoval(self):
        self.connectClient("chanop", name="chanop")
        mode = self.getInviteExceptionMode()

        # Create channel and set invite-only mode with exception
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +i")
        self.getMessages("chanop")

        self.sendLine("chanop", f"MODE #chan +{mode} bar!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"+{mode}", "bar!*@*"],
        )

        # User can join via exception
        self.connectClient("Bar", name="bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")

        # User leaves
        self.sendLine("bar", "PART #chan")
        self.getMessages("bar")
        self.getMessages("chanop")

        # Remove the exception
        self.sendLine("chanop", f"MODE #chan -{mode} bar!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"-{mode}", "bar!*@*"],
        )

        # User should now be blocked
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_INVITEONLYCHAN)

    @cases.mark_specifications("Modern")
    def testInviteExceptionWithoutInviteOnly(self):
        self.connectClient("chanop", name="chanop")
        mode = self.getInviteExceptionMode()

        # Create channel without invite-only mode
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        # Set invite exception (should be allowed but has no effect)
        self.sendLine("chanop", f"MODE #chan +{mode} bar!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"+{mode}", "bar!*@*"],
        )

        # User should be able to join regardless (channel is not +i)
        self.connectClient("Baz", name="baz")
        self.sendLine("baz", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("baz"), command="JOIN")

    @cases.mark_specifications("Modern")
    def testInviteExceptionMultipleMasks(self):
        self.connectClient("chanop", name="chanop")
        mode = self.getInviteExceptionMode()

        # Create channel and set invite-only mode
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan +i")
        self.getMessages("chanop")

        # Set exception for bar!*@* but not baz!*@*
        self.sendLine("chanop", f"MODE #chan +{mode} bar!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"+{mode}", "bar!*@*"],
        )

        # bar should be able to join
        self.connectClient("Bar", name="bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")
        self.getMessages("chanop")

        # baz should be blocked
        self.connectClient("Baz", name="baz")
        self.sendLine("baz", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("baz"), command=ERR_INVITEONLYCHAN)

        # Add exception for baz!*@*
        self.sendLine("chanop", f"MODE #chan +{mode} baz!*@*")
        self.assertMessageMatch(
            self.getMessage("chanop"),
            command="MODE",
            params=["#chan", f"+{mode}", "baz!*@*"],
        )

        # baz should now be able to join
        self.sendLine("baz", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("baz"), command="JOIN")
