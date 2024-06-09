from irctest import cases
from irctest.numerics import (
    ERR_CHANOPRIVSNEEDED,
    ERR_NOSUCHCHANNEL,
    ERR_NOSUCHNICK,
    ERR_NOTONCHANNEL,
    ERR_USERNOTINCHANNEL,
)


class ChannelOperatorModeTestCase(cases.BaseServerTestCase):
    """Test various error and success cases around the channel operator mode:
    <https://modern.ircdocs.horse/#channel-operators>
    <https://modern.ircdocs.horse/#mode-message>
    """

    def setupNicks(self):
        """Set up a standard set of three nicknames and two channels
        for testing channel-user MODE interactions."""
        # first nick to join the channel is privileged:
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")

        self.connectClient("unprivileged", name="unprivileged")
        self.joinChannel("unprivileged", "#chan")
        self.getMessages("chanop")

        self.connectClient("unrelated", name="unrelated")
        self.joinChannel("unrelated", "#unrelated")
        self.joinChannel("unprivileged", "#unrelated")
        self.getMessages("unrelated")

    @cases.mark_specifications("Modern")
    @cases.xfailIfSoftware(["irc2"], "broken in irc2")
    def testChannelOperatorModeSenderPrivsNeeded(self):
        """Test that +o from a channel member without the necessary privileges
        fails as expected."""
        self.setupNicks()
        # sender is a channel member but without the necessary privileges:
        self.sendLine("unprivileged", "MODE #chan +o unprivileged")
        messages = self.getMessages("unprivileged")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_CHANOPRIVSNEEDED)

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeTargetNotInChannel(self):
        """Test that +o targeting a user not present in the channel fails
        as expected."""
        self.setupNicks()
        # sender is a chanop, but target nick is not in the channel:
        self.sendLine("chanop", "MODE #chan +o unrelated")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_USERNOTINCHANNEL)

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeTargetDoesNotExist(self):
        """Test that +o targeting a nonexistent nick fails as expected."""
        self.setupNicks()
        # sender is a chanop, but target nick does not exist:
        self.sendLine("chanop", "MODE #chan +o nobody")
        messages = self.getMessages("chanop")
        # ERR_NOSUCHNICK is typical, Bahamut additionally sends ERR_USERNOTINCHANNEL
        if self.controller.software_name != "Bahamut":
            self.assertEqual(len(messages), 1)
            self.assertMessageMatch(messages[0], command=ERR_NOSUCHNICK)
        else:
            self.assertLessEqual(len(messages), 2)
            commands = {message.command for message in messages}
            self.assertLessEqual({ERR_NOSUCHNICK}, commands)
            self.assertLessEqual(commands, {ERR_NOSUCHNICK, ERR_USERNOTINCHANNEL})

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeChannelDoesNotExist(self):
        """Test that +o targeting a nonexistent channel fails as expected."""
        self.setupNicks()
        # target channel does not exist, but target nick does:
        self.sendLine("chanop", "MODE #nonexistentchan +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        # Modern: "If <target> is a channel that does not exist on the network,
        # the ERR_NOSUCHCHANNEL (403) numeric is returned."
        # However, Unreal sends 401 ERR_NOSUCHNICK here instead:
        if self.controller.software_name != "UnrealIRCd":
            self.assertEqual(messages[0].command, ERR_NOSUCHCHANNEL)
        else:
            self.assertIn(messages[0].command, [ERR_NOSUCHCHANNEL, ERR_NOSUCHNICK])

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeChannelAndTargetDoNotExist(self):
        """Test that +o targeting a nonexistent channel and nickname
        fails as expected."""
        self.setupNicks()
        # neither target channel nor target nick exist:
        self.sendLine("chanop", "MODE #nonexistentchan +o nobody")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(
            messages[0].command,
            [ERR_NOSUCHCHANNEL, ERR_NOTONCHANNEL, ERR_NOSUCHNICK, ERR_USERNOTINCHANNEL],
        )

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeSenderNonMember(self):
        """Test that +o where the sender is not a channel member
        fails as expected."""
        self.setupNicks()
        # sender is not a channel member, target nick exists and is a channel member:
        self.sendLine("chanop", "MODE #unrelated +o unprivileged")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(messages[0].command, [ERR_NOTONCHANNEL, ERR_CHANOPRIVSNEEDED])

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeSenderAndTargetNonMembers(self):
        """Test that +o where neither the sender nor the target is a channel
        member fails as expected."""
        self.setupNicks()
        # sender is not a channel member, target nick exists but is not a channel member:
        self.sendLine("chanop", "MODE #unrelated +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(
            messages[0].command,
            [ERR_NOTONCHANNEL, ERR_CHANOPRIVSNEEDED, ERR_USERNOTINCHANNEL],
        )

    @cases.mark_specifications("Modern")
    def testChannelOperatorModeSuccess(self):
        """Tests a successful grant of +o in a channel."""
        self.setupNicks()

        self.sendLine("chanop", "MODE #chan +o unprivileged")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(
            messages[0],
            command="MODE",
            params=["#chan", "+o", "unprivileged"],
        )
        messages = self.getMessages("unprivileged")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(
            messages[0],
            command="MODE",
            params=["#chan", "+o", "unprivileged"],
        )
