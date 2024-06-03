"""
Test various error and success cases around the channel operator mode:
<https://modern.ircdocs.horse/#channel-operators>
<https://modern.ircdocs.horse/#mode-message>
"""

from irctest import cases
from irctest.numerics import (
    ERR_CHANOPRIVSNEEDED,
    ERR_NOSUCHCHANNEL,
    ERR_NOSUCHNICK,
    ERR_NOTONCHANNEL,
    ERR_USERNOTINCHANNEL,
)


class ChannelOperatorModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testChannelOperatorMode(self):
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")

        self.connectClient("unprivd", name="unprivd")
        self.joinChannel("unprivd", "#chan")
        self.getMessages("chanop")

        self.connectClient("otherguy", name="otherguy")
        self.joinChannel("otherguy", "#otherguy")

        # sender is a channel member but without the necessary privileges:
        self.sendLine("unprivd", "MODE #chan +o unprivd")
        messages = self.getMessages("unprivd")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_CHANOPRIVSNEEDED)

        # sender is a chanop, but target nick is not in the channel:
        self.sendLine("chanop", "MODE #chan +o otherguy")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_USERNOTINCHANNEL)

        # sender is a chanop, but target nick does not exist:
        self.sendLine("chanop", "MODE #chan +o nobody")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(messages[0].command, [ERR_NOSUCHNICK, ERR_USERNOTINCHANNEL])

        # target channel does not exist, but target nick does:
        self.sendLine("chanop", "MODE #nonexistentchan +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        # Modern: "If <target> is a channel that does not exist on the network,
        # the ERR_NOSUCHCHANNEL (403) numeric is returned."
        # However, Unreal sends 401 ERR_NOSUCHNICK here instead:
        self.assertIn(messages[0].command, [ERR_NOSUCHCHANNEL, ERR_NOSUCHNICK])

        # neither target channel nor target nick exist:
        self.sendLine("chanop", "MODE #nonexistentchan +o nobody")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(
            messages[0].command,
            [ERR_NOSUCHCHANNEL, ERR_NOTONCHANNEL, ERR_NOSUCHNICK, ERR_USERNOTINCHANNEL],
        )

        # sender is not a channel member, target nick exists but is not a channel member:
        self.sendLine("chanop", "MODE #otherguy +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(messages[0].command, [ERR_NOTONCHANNEL, ERR_CHANOPRIVSNEEDED])

        # test an actually successful mode grant:
        self.sendLine("chanop", "MODE #chan +o unprivd")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(
            messages[0],
            command="MODE",
            params=["#chan", "+o", "unprivd"],
        )
        messages = self.getMessages("unprivd")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(
            messages[0],
            command="MODE",
            params=["#chan", "+o", "unprivd"],
        )
