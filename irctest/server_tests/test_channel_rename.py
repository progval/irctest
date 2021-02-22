from irctest import cases
from irctest.numerics import ERR_CHANOPRIVSNEEDED

MODERN_CAPS = [
    "server-time",
    "message-tags",
    "batch",
    "labeled-response",
    "echo-message",
    "account-tag",
]
RENAME_CAP = "draft/channel-rename"


class ChannelRename(cases.BaseServerTestCase):
    """Basic tests for channel-rename."""

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
    def testChannelRename(self):
        self.connectClient("bar", name="bar", capabilities=MODERN_CAPS + [RENAME_CAP])
        self.connectClient("baz", name="baz", capabilities=MODERN_CAPS)
        self.joinChannel("bar", "#bar")
        self.joinChannel("baz", "#bar")
        self.getMessages("bar")
        self.getMessages("baz")

        self.sendLine("bar", "RENAME #bar #qux :no reason")
        self.assertMessageEqual(
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
