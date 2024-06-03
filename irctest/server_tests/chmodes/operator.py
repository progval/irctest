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

        self.sendLine("unprivd", "MODE #chan +o unprivd")
        messages = self.getMessages("unprivd")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_CHANOPRIVSNEEDED)

        self.sendLine("chanop", "MODE #chan +o otherguy")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_USERNOTINCHANNEL)

        self.sendLine("chanop", "MODE #nonexistentchan +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        # Modern: "If <target> is a channel that does not exist on the network,
        # the ERR_NOSUCHCHANNEL (403) numeric is returned."
        self.assertMessageMatch(messages[0], command=ERR_NOSUCHCHANNEL)

        self.sendLine("chanop", "MODE #nonexistentchan +o nonexistentnick")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(
            messages[0].command,
            [ERR_NOSUCHCHANNEL, ERR_NOTONCHANNEL, ERR_NOSUCHNICK, ERR_USERNOTINCHANNEL],
        )

        self.sendLine("chanop", "MODE #otherguy +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(messages[0].command, [ERR_NOTONCHANNEL, ERR_CHANOPRIVSNEEDED])

        # test an actually successful mode grant
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
