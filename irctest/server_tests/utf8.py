"""
`Ergo <https://ergo.chat/>`_-specific tests of non-Unicode filtering

<https://ircv3.net/specs/extensions/utf8-only>`_
"""

from irctest import cases, runner
from irctest.numerics import ERR_ERRONEUSNICKNAME
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
        self.sendLine(2, "NICK bar")
        self.clients[2].conn.sendall(b"USER username * * :i\xe8rc\xe9\r\n")

        d = self.clients[2].conn.recv(1024)
        if b"FAIL " in d or b"468 " in d:  # ERR_INVALIDUSERNAME
            return  # nothing more to test
        self.assertIn(b"001 ", d)

        self.sendLine(2, "WHOIS bar")
        self.getMessages(2)

    def testNonutf8Username(self):
        self.connectClient("foo")
        if "UTF8ONLY" not in self.server_support:
            raise runner.IsupportTokenNotSupported("UTF8ONLY")

        self.addClient()
        self.sendLine(2, "NICK bar")
        self.sendLine(2, "USER 😊😊😊😊😊😊😊😊😊😊 * * :realname")
        m = self.getRegistrationMessage(2)
        if m.command in ("FAIL", "468"):  # ERR_INVALIDUSERNAME
            return  # nothing more to test
        self.assertMessageMatch(
            m,
            command="001",
        )
        self.sendLine(2, "WHOIS bar")
        self.getMessages(2)


class ErgoUtf8NickEnabledTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["server"].update(
                {"casemapping": "precis"},
            )
        )

    @cases.mark_specifications("Ergo")
    def testUtf8NonAsciiNick(self):
        """Ergo accepts certain non-ASCII UTF8 nicknames if PRECIS is enabled."""
        self.connectClient("Işıl")
        self.joinChannel(1, "#test")

        self.connectClient("Claire")
        self.joinChannel(2, "#test")

        self.sendLine(1, "PRIVMSG #test :hi there")
        self.getMessages(1)
        self.assertMessageMatch(
            self.getMessage(2), nick="Işıl", params=["#test", "hi there"]
        )


class ErgoUtf8NickDisabledTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testUtf8NonAsciiNick(self):
        """Ergo rejects non-ASCII nicknames in its default configuration."""
        self.addClient(1)
        self.sendLine(1, "USER u s e r")
        self.sendLine(1, "NICK Işıl")
        self.assertMessageMatch(self.getMessage(1), command=ERR_ERRONEUSNICKNAME)
