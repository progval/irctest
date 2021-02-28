"""
This specification is a little hard to test because all labels are optional;
so there may be many false positives.

<https://ircv3.net/specs/extensions/labeled-response.html>
"""

import re

from irctest import cases
from irctest.patma import StrRe


class LabeledResponsesTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    def connectClient(self, nick, *, capabilities, **kwargs):
        if self.controller.software_name == "InspIRCd":
            # InspIRCd only sends labels if 'batch' is enabled
            if "batch" not in capabilities:
                capabilities.append("batch")
        return super().connectClient(nick, capabilities=capabilities, **kwargs)

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledPrivmsgResponsesToMultipleClients(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)
        self.connectClient(
            "carl",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(3)
        self.connectClient(
            "alice",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(4)

        self.sendLine(1, "@label=12345 PRIVMSG bar,carl,alice :hi")
        m = self.getMessage(1)
        m2 = self.getMessage(2)
        m3 = self.getMessage(3)
        m4 = self.getMessage(4)

        # ensure the label isn't sent to recipients
        self.assertMessageMatch(
            m2,
            command="PRIVMSG",
            fail_msg="No PRIVMSG received by target 1 after sending one out",
        )
        self.assertNotIn(
            "label",
            m2.tags,
            m2,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the target users shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )
        self.assertMessageMatch(
            m3,
            command="PRIVMSG",
            fail_msg="No PRIVMSG received by target 1 after sending one out",
        )
        self.assertNotIn(
            "label",
            m3.tags,
            m3,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the target users shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )
        self.assertMessageMatch(
            m4,
            command="PRIVMSG",
            fail_msg="No PRIVMSG received by target 1 after sending one out",
        )
        self.assertNotIn(
            "label",
            m4.tags,
            m4,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the target users shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )

        self.assertMessageMatch(
            m, command="BATCH", fail_msg="No BATCH echo received after sending one out"
        )

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledPrivmsgResponsesToClient(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        self.sendLine(1, "@label=12345 PRIVMSG bar :hi")
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            m2,
            command="PRIVMSG",
            fail_msg="No PRIVMSG received by the target after sending one out",
        )
        self.assertNotIn(
            "label",
            m2.tags,
            m2,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the target user shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )

        self.assertMessageMatch(
            m,
            command="PRIVMSG",
            fail_msg="No PRIVMSG echo received after sending one out",
        )
        self.assertIn(
            "label",
            m.tags,
            m,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the echo'd message didn't contain the label at all: {msg}"
            ),
        )
        self.assertEqual(
            m.tags["label"],
            "12345",
            m,
            fail_msg=(
                "Echo'd PRIVMSG to a client did not contain the same label "
                "we sent it with(should be '12345'): {msg}"
            ),
        )

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledPrivmsgResponsesToChannel(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        # join channels
        self.sendLine(1, "JOIN #test")
        self.getMessages(1)
        self.sendLine(2, "JOIN #test")
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(
            1, "@label=12345;+draft/reply=123;+draft/react=l😃l PRIVMSG #test :hi"
        )
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            mt,
            command="PRIVMSG",
            fail_msg="No PRIVMSG received by the target after sending one out",
        )
        self.assertNotIn(
            "label",
            mt.tags,
            mt,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the target user shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )

        # ensure sender correctly receives msg
        self.assertMessageMatch(
            ms, command="PRIVMSG", fail_msg="Got a message back that wasn't a PRIVMSG"
        )
        self.assertIn(
            "label",
            ms.tags,
            ms,
            fail_msg=(
                "When sending a PRIVMSG with a label, "
                "the source user should receive the label but didn't: {msg}"
            ),
        )
        self.assertEqual(
            ms.tags["label"],
            "12345",
            ms,
            fail_msg=(
                "Echo'd label doesn't match the label we sent "
                "(should be '12345'): {msg}"
            ),
        )

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledPrivmsgResponsesToSelf(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)

        self.sendLine(1, "@label=12345 PRIVMSG foo :hi")
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)

        number_of_labels = 0
        for m in [m1, m2]:
            self.assertMessageMatch(
                m,
                command="PRIVMSG",
                fail_msg="Got a message back that wasn't a PRIVMSG",
            )
            if "label" in m.tags:
                number_of_labels += 1
                self.assertEqual(
                    m.tags["label"],
                    "12345",
                    m,
                    fail_msg=(
                        "Echo'd label doesn't match the label we sent "
                        "(should be '12345'): {msg}"
                    ),
                )

        self.assertEqual(
            number_of_labels,
            1,
            m1,
            fail_msg=(
                "When sending a PRIVMSG to self with echo-message, "
                "we only expect one message to contain the label. "
                "Instead, {} messages had the label"
            ).format(number_of_labels),
        )

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledNoticeResponsesToClient(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        self.sendLine(1, "@label=12345 NOTICE bar :hi")
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            m2,
            command="NOTICE",
            fail_msg="No NOTICE received by the target after sending one out",
        )
        self.assertNotIn(
            "label",
            m2.tags,
            m2,
            fail_msg=(
                "When sending a NOTICE with a label, "
                "the target user shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )

        self.assertMessageMatch(
            m,
            command="NOTICE",
            fail_msg="No NOTICE echo received after sending one out",
        )
        self.assertIn(
            "label",
            m.tags,
            m,
            fail_msg=(
                "When sending a NOTICE with a label, "
                "the echo'd message didn't contain the label at all: {msg}"
            ),
        )
        self.assertEqual(
            m.tags["label"],
            "12345",
            m,
            fail_msg=(
                "Echo'd NOTICE to a client did not contain the same label "
                "we sent it with (should be '12345'): {msg}"
            ),
        )

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledNoticeResponsesToChannel(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        # join channels
        self.sendLine(1, "JOIN #test")
        self.getMessages(1)
        self.sendLine(2, "JOIN #test")
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(
            1, "@label=12345;+draft/reply=123;+draft/react=l😃l NOTICE #test :hi"
        )
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            mt,
            command="NOTICE",
            fail_msg="No NOTICE received by the target after sending one out",
        )
        self.assertNotIn(
            "label",
            mt.tags,
            mt,
            fail_msg=(
                "When sending a NOTICE with a label, "
                "the target user shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )

        # ensure sender correctly receives msg
        self.assertMessageMatch(
            ms, command="NOTICE", fail_msg="Got a message back that wasn't a NOTICE"
        )
        self.assertIn(
            "label",
            ms.tags,
            ms,
            fail_msg=(
                "When sending a NOTICE with a label, "
                "the source user should receive the label but didn't: {msg}"
            ),
        )
        self.assertEqual(
            ms.tags["label"],
            "12345",
            ms,
            fail_msg=(
                "Echo'd label doesn't match the label we sent "
                "(should be '12345'): {msg}"
            ),
        )

    @cases.mark_capabilities("echo-message", "labeled-response")
    def testLabeledNoticeResponsesToSelf(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)

        self.sendLine(1, "@label=12345 NOTICE foo :hi")
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)

        number_of_labels = 0
        for m in [m1, m2]:
            self.assertMessageMatch(
                m, command="NOTICE", fail_msg="Got a message back that wasn't a NOTICE"
            )
            if "label" in m.tags:
                number_of_labels += 1
                self.assertEqual(
                    m.tags["label"],
                    "12345",
                    m,
                    fail_msg=(
                        "Echo'd label doesn't match the label we sent "
                        "(should be '12345'): {msg}"
                    ),
                )

        self.assertEqual(
            number_of_labels,
            1,
            m1,
            fail_msg=(
                "When sending a NOTICE to self with echo-message, "
                "we only expect one message to contain the label. "
                "Instead, {} messages had the label"
            ).format(number_of_labels),
        )

    @cases.mark_capabilities("echo-message", "labeled-response", "message-tags")
    def testLabeledTagMsgResponsesToClient(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        self.sendLine(1, "@label=12345;+draft/reply=123;+draft/react=l😃l TAGMSG bar")
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            m2,
            command="TAGMSG",
            fail_msg="No TAGMSG received by the target after sending one out",
        )
        self.assertNotIn(
            "label",
            m2.tags,
            m2,
            fail_msg=(
                "When sending a TAGMSG with a label, "
                "the target user shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )
        self.assertIn(
            "+draft/reply",
            m2.tags,
            m2,
            fail_msg="Reply tag wasn't present on the target user's TAGMSG: {msg}",
        )
        self.assertEqual(
            m2.tags["+draft/reply"],
            "123",
            m2,
            fail_msg="Reply tag wasn't the same on the target user's TAGMSG: {msg}",
        )
        self.assertIn(
            "+draft/react",
            m2.tags,
            m2,
            fail_msg="React tag wasn't present on the target user's TAGMSG: {msg}",
        )
        self.assertEqual(
            m2.tags["+draft/react"],
            "l😃l",
            m2,
            fail_msg="React tag wasn't the same on the target user's TAGMSG: {msg}",
        )

        self.assertMessageMatch(
            m,
            command="TAGMSG",
            fail_msg="No TAGMSG echo received after sending one out",
        )
        self.assertIn(
            "label",
            m.tags,
            m,
            fail_msg=(
                "When sending a TAGMSG with a label, "
                "the echo'd message didn't contain the label at all: {msg}"
            ),
        )
        self.assertEqual(
            m.tags["label"],
            "12345",
            m,
            fail_msg=(
                "Echo'd TAGMSG to a client did not contain the same label "
                "we sent it with (should be '12345'): {msg}"
            ),
        )
        self.assertIn(
            "+draft/reply",
            m.tags,
            m,
            fail_msg="Reply tag wasn't present on the source user's TAGMSG: {msg}",
        )
        self.assertEqual(
            m2.tags["+draft/reply"],
            "123",
            m,
            fail_msg="Reply tag wasn't the same on the source user's TAGMSG: {msg}",
        )
        self.assertIn(
            "+draft/react",
            m.tags,
            m,
            fail_msg="React tag wasn't present on the source user's TAGMSG: {msg}",
        )
        self.assertEqual(
            m2.tags["+draft/react"],
            "l😃l",
            m,
            fail_msg="React tag wasn't the same on the source user's TAGMSG: {msg}",
        )

    @cases.mark_capabilities("echo-message", "labeled-response", "message-tags")
    def testLabeledTagMsgResponsesToChannel(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        # join channels
        self.sendLine(1, "JOIN #test")
        self.getMessages(1)
        self.sendLine(2, "JOIN #test")
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, "@label=12345;+draft/reply=123;+draft/react=l😃l TAGMSG #test")
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            mt,
            command="TAGMSG",
            fail_msg="No TAGMSG received by the target after sending one out",
        )
        self.assertNotIn(
            "label",
            mt.tags,
            mt,
            fail_msg=(
                "When sending a TAGMSG with a label, "
                "the target user shouldn't receive the label "
                "(only the sending user should): {msg}"
            ),
        )

        # ensure sender correctly receives msg
        self.assertMessageMatch(
            ms, command="TAGMSG", fail_msg="Got a message back that wasn't a TAGMSG"
        )
        self.assertIn(
            "label",
            ms.tags,
            ms,
            fail_msg=(
                "When sending a TAGMSG with a label, "
                "the source user should receive the label but didn't: {msg}"
            ),
        )
        self.assertEqual(
            ms.tags["label"],
            "12345",
            ms,
            fail_msg=(
                "Echo'd label doesn't match the label we sent "
                "(should be '12345'): {msg}"
            ),
        )

    @cases.mark_capabilities("echo-message", "labeled-response", "message-tags")
    def testLabeledTagMsgResponsesToSelf(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)

        self.sendLine(1, "@label=12345;+draft/reply=123;+draft/react=l😃l TAGMSG foo")
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)

        number_of_labels = 0
        for m in [m1, m2]:
            self.assertMessageMatch(
                m, command="TAGMSG", fail_msg="Got a message back that wasn't a TAGMSG"
            )
            if "label" in m.tags:
                number_of_labels += 1
                self.assertEqual(
                    m.tags["label"],
                    "12345",
                    m,
                    fail_msg=(
                        "Echo'd label doesn't match the label we sent "
                        "(should be '12345'): {msg}"
                    ),
                )

        self.assertEqual(
            number_of_labels,
            1,
            m1,
            fail_msg=(
                "When sending a TAGMSG to self with echo-message, "
                "we only expect one message to contain the label. "
                "Instead, {} messages had the label"
            ).format(number_of_labels),
        )

    @cases.mark_capabilities("batch", "labeled-response", "message-tags", "server-time")
    def testBatchedJoinMessages(self):
        self.connectClient(
            "bar",
            capabilities=["batch", "labeled-response", "message-tags", "server-time"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)

        self.sendLine(1, "@label=12345 JOIN #xyz")
        m = self.getMessages(1)

        # we expect at least join and names lines, which must be batched
        self.assertGreaterEqual(len(m), 3)

        # valid BATCH start line:
        batch_start = m[0]
        self.assertMessageMatch(
            batch_start,
            command="BATCH",
            params=[StrRe(r"\+.*"), "labeled-response"],
        )
        batch_id = batch_start.params[0][1:]
        # batch id MUST be alphanumerics and hyphens
        self.assertTrue(
            re.match(r"^[A-Za-z0-9\-]+$", batch_id) is not None,
            "batch id must be alphanumerics and hyphens, got %r" % (batch_id,),
        )
        self.assertEqual(batch_start.tags.get("label"), "12345")

        # valid BATCH end line
        batch_end = m[-1]
        self.assertMessageMatch(batch_end, command="BATCH", params=["-" + batch_id])

        # messages must have the BATCH tag
        for message in m[1:-1]:
            self.assertEqual(message.tags.get("batch"), batch_id)

    @cases.mark_capabilities("labeled-response")
    def testNoBatchForSingleMessage(self):
        self.connectClient(
            "bar", capabilities=["labeled-response"], skip_if_cap_nak=True
        )
        self.getMessages(1)

        self.sendLine(1, "@label=98765 PING adhoctestline")
        # no BATCH should be initiated for a one-line response,
        # it should just be labeled
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        m = ms[0]
        self.assertEqual(m.command, "PONG")
        self.assertEqual(m.params[-1], "adhoctestline")

        # check the label
        self.assertEqual(m.tags.get("label"), "98765")

    @cases.mark_capabilities("labeled-response")
    def testEmptyBatchForNoResponse(self):
        self.connectClient(
            "bar", capabilities=["labeled-response"], skip_if_cap_nak=True
        )
        self.getMessages(1)

        # PONG never receives a response
        self.sendLine(1, "@label=98765 PONG adhoctestline")

        # labeled-response: "Servers MUST respond with a labeled
        # `ACK` message when a client sends a labeled command that normally
        # produces no response."
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        ack = ms[0]

        self.assertEqual(ack.command, "ACK")
        self.assertEqual(ack.tags.get("label"), "98765")
