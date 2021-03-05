"""
Section 3.2 of RFC 2812
<https://tools.ietf.org/html/rfc2812#section-3.3>
"""

from irctest import cases
from irctest.numerics import ERR_INPUTTOOLONG


class PrivmsgTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testPrivmsg(self):
        """<https://tools.ietf.org/html/rfc2812#section-3.3.1>"""
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        self.connectClient("bar")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)  # synchronize
        self.sendLine(1, "PRIVMSG #chan :hello there")
        self.getMessages(1)  # synchronize
        pms = [msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"]
        self.assertEqual(len(pms), 1)
        self.assertMessageMatch(
            pms[0], command="PRIVMSG", params=["#chan", "hello there"]
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testPrivmsgNonexistentChannel(self):
        """<https://tools.ietf.org/html/rfc2812#section-3.3.1>"""
        self.connectClient("foo")
        self.sendLine(1, "PRIVMSG #nonexistent :hello there")
        msg = self.getMessage(1)
        # ERR_NOSUCHNICK, ERR_NOSUCHCHANNEL, or ERR_CANNOTSENDTOCHAN
        self.assertIn(msg.command, ("401", "403", "404"))


class NoticeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testNotice(self):
        """<https://tools.ietf.org/html/rfc2812#section-3.3.2>"""
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        self.connectClient("bar")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)  # synchronize
        self.sendLine(1, "NOTICE #chan :hello there")
        self.getMessages(1)  # synchronize
        notices = [msg for msg in self.getMessages(2) if msg.command == "NOTICE"]
        self.assertEqual(len(notices), 1)
        self.assertMessageMatch(
            notices[0], command="NOTICE", params=["#chan", "hello there"]
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testNoticeNonexistentChannel(self):
        """
        "automatic replies must never be
        sent in response to a NOTICE message.  This rule applies to servers
        too - they must not send any error reply back to the client on
        receipt of a notice"
        <https://tools.ietf.org/html/rfc1459#section-4.4.2>

        'automatic replies MUST NEVER be sent in response to a NOTICE message.
        This rule applies to servers too - they MUST NOT send any error repl
        back to the client on receipt of a notice."
        <https://tools.ietf.org/html/rfc2812#section-3.3.2>
        """
        self.connectClient("foo")
        self.sendLine(1, "NOTICE #nonexistent :hello there")
        self.assertEqual(self.getMessages(1), [])


class TagsTestCase(cases.BaseServerTestCase):
    @cases.mark_capabilities("message-tags")
    def testLineTooLong(self):
        self.connectClient("bar", capabilities=["message-tags"], skip_if_cap_nak=True)
        self.joinChannel(1, "#xyz")
        monsterMessage = "@+clientOnlyTagExample=" + "a" * 4096 + " PRIVMSG #xyz hi!"
        self.sendLine(1, monsterMessage)
        replies = self.getMessages(1)
        self.assertIn(ERR_INPUTTOOLONG, set(reply.command for reply in replies))


class LengthLimitTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Oragono")
    def testLineAtLimit(self):
        self.connectClient("bar", name="bar")
        self.getMessages("bar")
        line = "PING " + ("x" * (512 - 7))
        # this line is exactly as the limit, after including \r\n:
        self.assertEqual(len(line), 510)
        # oragono should accept and process this message. the outgoing PONG
        # will be truncated due to the addition of the server name as source
        # and initial parameter; this is fine:
        self.sendLine("bar", line)
        result = self.getMessage("bar", synchronize=False)
        self.assertMessageMatch(result, command="PONG")
        self.assertIn("x" * 450, result.params[-1])

    @cases.mark_specifications("Oragono")
    def testLineBeyondLimit(self):
        self.connectClient("bar", name="bar")
        self.getMessages("bar")
        line = "PING " + ("x" * (512 - 6))
        # this line is one over the limit after including \r\n:
        self.assertEqual(len(line), 511)
        # oragono should reject this message for exceeding the length limit:
        self.sendLine("bar", line)
        result = self.getMessage("bar", synchronize=False)
        self.assertMessageMatch(result, command=ERR_INPUTTOOLONG)
        # we should not be disconnected and should be able to join a channel
        self.joinChannel("bar", "#test_channel")
