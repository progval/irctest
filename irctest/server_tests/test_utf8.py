from irctest import cases
from irctest.patma import ANYSTR


class Utf8TestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.mark_specifications("Oragono")
    def testUtf8Validation(self):
        self.connectClient(
            "bar",
            capabilities=["batch", "echo-message", "labeled-response"],
        )
        self.joinChannel(1, "#qux")
        self.sendLine(1, "PRIVMSG #qux hi")
        ms = self.getMessages(1)
        self.assertMessageMatch(
            [m for m in ms if m.command == "PRIVMSG"][0], params=["#qux", "hi"]
        )

        self.sendLine(1, b"PRIVMSG #qux hi\xaa")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["PRIVMSG", "INVALID_UTF8", ANYSTR],
            tags={},
        )

        self.sendLine(1, b"@label=xyz PRIVMSG #qux hi\xaa")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["PRIVMSG", "INVALID_UTF8", ANYSTR],
            tags={"label": "xyz"},
        )
