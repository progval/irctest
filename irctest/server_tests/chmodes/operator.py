"""
Test various error and success cases around the channel operator mode:
<https://modern.ircdocs.horse/#channel-operators>
<https://modern.ircdocs.horse/#mode-message>
"""

from irctest import cases
from irctest.numerics import (
    ERR_CHANOPRIVSNEEDED,
    ERR_USERNOTINCHANNEL,
    ERR_NOSUCHNICK,
    ERR_NOSUCHCHANNEL,
    ERR_NOTONCHANNEL,
)


class ChannelOperatorModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459")
    def testChannelOperatorMode(self):
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")

        self.connectClient("unprivileged", name="unprivileged")
        self.joinChannel("unprivileged", "#chan")
        self.getMessages("chanop")

        self.connectClient("unrelated", name="unrelated")
        self.joinChannel("unrelated", "#unrelated")

        self.sendLine("unprivileged", "MODE #chan +o unprivileged")
        messages = self.getMessages("unprivileged")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_CHANOPRIVSNEEDED)

        self.sendLine("chanop", "MODE #chan +o unrelated")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertMessageMatch(messages[0], command=ERR_USERNOTINCHANNEL)

        self.sendLine("chanop", "MODE #nonexistentchan +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(messages[0].command, [ERR_NOSUCHCHANNEL, ERR_CHANOPRIVSNEEDED])

        self.sendLine("chanop", "MODE #nonexistentchan +o nonexistentnick")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(
            messages[0].command,
            [ERR_NOSUCHCHANNEL, ERR_NOTONCHANNEL, ERR_NOSUCHNICK, ERR_USERNOTINCHANNEL],
        )

        self.sendLine("chanop", "MODE #unrelated +o chanop")
        messages = self.getMessages("chanop")
        self.assertEqual(len(messages), 1)
        self.assertIn(messages[0].command, [ERR_NOTONCHANNEL, ERR_CHANOPRIVSNEEDED])

        # test an actually successful mode grant
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
