from irctest import cases


class Utf8TestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.mark_specifications("Oragono")
    def testUtf8Validation(self):
        self.connectClient(
            "bar",
            capabilities=["batch", "echo-message", "labeled-response", "message-tags"],
        )
        self.joinChannel(1, "#qux")
        self.sendLine(1, "PRIVMSG #qux hi")
        ms = self.getMessages(1)
        self.assertMessageEqual(
            [m for m in ms if m.command == "PRIVMSG"][0], params=["#qux", "hi"]
        )

        self.sendLine(1, b"PRIVMSG #qux hi\xaa")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0].command, "FAIL")
        self.assertEqual(ms[0].params[:2], ["PRIVMSG", "INVALID_UTF8"])

        self.sendLine(1, b"@label=xyz PRIVMSG #qux hi\xaa")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0].command, "FAIL")
        self.assertEqual(ms[0].params[:2], ["PRIVMSG", "INVALID_UTF8"])
        self.assertEqual(ms[0].tags.get("label"), "xyz")
