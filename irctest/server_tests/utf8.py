"""
`Ergo <https://ergo.chat/>`_-specific tests of non-Unicode filtering

<https://ircv3.net/specs/extensions/utf8-only>`_
"""

from irctest import cases
from irctest.patma import ANYSTR


class Utf8TestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testNonUnicodeFiltering(self):
        self.connectClient(
            "bar",
            capabilities=["batch", "echo-message", "labeled-response"],
        )
        self.joinChannel(1, "#qux")
        self.sendLine(1, b"@label=xyz PRIVMSG #qux hi\xaa")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["PRIVMSG", "INVALID_UTF8", ANYSTR],
            tags={"label": "xyz"},
        )

    @cases.mark_isupport("UTF8ONLY")
    @cases.mark_capabilities("echo-message")
    def testUtf8Validation(self):
        self.connectClient(
            "bar",
            capabilities=["echo-message"],
        )
        self.joinChannel(1, "#qux")
        self.sendLine(1, "PRIVMSG #qux hi")
        ms = self.getMessages(1)
        self.assertMessageMatch(
            [m for m in ms if m.command == "PRIVMSG"][0], params=["#qux", "hi"]
        )

        self.sendLine(1, b"PRIVMSG #qux hi\xaa")

        m = self.getMessage(1)
        assert m.command in ("FAIL", "WARN", "ERROR")

        if m.command in ("FAIL", "WARN"):
            self.assertMessageMatch(m, params=["PRIVMSG", "INVALID_UTF8", ANYSTR])
