"""
`Draft IRCv3 channel-rename <https://ircv3.net/specs/extensions/channel-rename>`_
"""

from irctest import cases
from irctest.numerics import ERR_CHANOPRIVSNEEDED

RENAME_CAP = "draft/channel-rename"


@cases.mark_specifications("IRCv3")
class ChannelRenameTestCase(cases.BaseServerTestCase):
    """Basic tests for channel-rename."""

    def testChannelRename(self):
        self.connectClient(
            "bar", name="bar", capabilities=[RENAME_CAP], skip_if_cap_nak=True
        )
        self.connectClient("baz", name="baz")
        self.joinChannel("bar", "#bar")
        self.joinChannel("baz", "#bar")
        self.getMessages("bar")
        self.getMessages("baz")

        self.sendLine("bar", "RENAME #bar #qux :no reason")
        self.assertMessageMatch(
            self.getMessage("bar"),
            command="RENAME",
            params=["#bar", "#qux", "no reason"],
        )
        legacy_responses = self.getMessages("baz")
        self.assertEqual(
            1,
            len(
                [
                    msg
                    for msg in legacy_responses
                    if msg.command == "PART" and msg.params[0] == "#bar"
                ]
            ),
        )
        self.assertEqual(
            1,
            len(
                [
                    msg
                    for msg in legacy_responses
                    if msg.command == "JOIN" and msg.params == ["#qux"]
                ]
            ),
        )

        self.joinChannel("baz", "#bar")
        self.sendLine("baz", "MODE #bar +k beer")
        self.assertNotIn(
            ERR_CHANOPRIVSNEEDED, [msg.command for msg in self.getMessages("baz")]
        )
