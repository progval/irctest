"""
`Ergo <https://ergo.chat/>`_-specific tests of non-Unicode filtering

<https://ircv3.net/specs/extensions/utf8-only>`_
"""

from irctest import cases, runner
from irctest.patma import ANYSTR


class Utf8TestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testNonUtf8Filtering(self):
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
    def testUtf8Validation(self):
        self.connectClient("foo")
        self.connectClient("bar")

        if "UTF8ONLY" not in self.server_support:
            raise runner.IsupportTokenNotSupported("UTF8ONLY")

        self.sendLine(1, "PRIVMSG bar hi")
        self.getMessages(1)  # synchronize
        ms = self.getMessages(2)
        self.assertMessageMatch(
            [m for m in ms if m.command == "PRIVMSG"][0], params=["bar", "hi"]
        )

        self.sendLine(1, b"PRIVMSG bar hi\xaa")

        m = self.getMessage(1)
        assert m.command in ("FAIL", "WARN", "ERROR")

        if m.command in ("FAIL", "WARN"):
            self.assertMessageMatch(m, params=["PRIVMSG", "INVALID_UTF8", ANYSTR])

    def testNonutf8Realname(self):
        self.connectClient("foo")
        if "UTF8ONLY" not in self.server_support:
            raise runner.IsupportTokenNotSupported("UTF8ONLY")

        self.addClient()
        self.sendLine(2, "NICK foo")
        self.clients[2].conn.sendall(b"USER username * * :i\xe8rc\xe9\r\n")

        d = self.clients[2].conn.recv(1024)
        if b" FAIL " in d or b" 468 " in d:  # ERR_INVALIDUSERNAME
            return  # nothing more to test
        self.assertIn(b" 001 ", d)

        self.sendLine(2, "WHOIS foo")
        self.getMessages(2)

    def testNonutf8Username(self):
        self.connectClient("foo")
        if "UTF8ONLY" not in self.server_support:
            raise runner.IsupportTokenNotSupported("UTF8ONLY")

        self.addClient()
        self.sendLine(2, "NICK foo")
        self.sendLine(2, "USER 😊😊😊😊😊😊😊😊😊😊 * * :realname")
        m = self.getRegistrationMessage(2)
        if m.command in ("FAIL", "468"):  # ERR_INVALIDUSERNAME
            return  # nothing more to test
        self.assertMessageMatch(
            m,
            command="001",
        )
        self.sendLine(2, "WHOIS foo")
        self.getMessages(2)
