"""
`IRCv3 labeled-response <https://ircv3.net/specs/extensions/labeled-response>`_

This specification is a little hard to test because all labels are optional;
so there may be many false positives.
"""

import re

import pytest

from irctest import cases, runner
from irctest.numerics import ERR_UNKNOWNCOMMAND
from irctest.patma import ANYDICT, ANYOPTSTR, NotStrRe, RemainingKeys, StrRe
from irctest.specifications import OptionalBehaviors


class LabeledResponsesTestCase(cases.BaseServerTestCase):
    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledPrivmsgResponsesToMultipleClients(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        if int(self.targmax.get("PRIVMSG", "1") or "4") < 3:
            raise runner.OptionalBehaviorNotSupported(OptionalBehaviors.MULTI_PRIVMSG)
        self.getMessages(1)

        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)
        self.connectClient(
            "carl",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(3)
        self.connectClient(
            "alice",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(4)

        self.sendLine(1, "@label=12345 PRIVMSG bar,carl,alice :hi")
        m = self.getMessage(1)
        m2 = self.getMessage(2)
        m3 = self.getMessage(3)
        m4 = self.getMessage(4)

        # ensure the label isn't sent to recipients
        self.assertMessageMatch(m2, command="PRIVMSG", tags={})
        self.assertMessageMatch(
            m3,
            command="PRIVMSG",
            tags={},
        )
        self.assertMessageMatch(m4, command="PRIVMSG", tags={})

        self.assertMessageMatch(
            m, command="BATCH", fail_msg="No BATCH echo received after sending one out"
        )

    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledPrivmsgResponsesToClient(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        self.sendLine(1, "@label=12345 PRIVMSG bar :hi")
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(m2, command="PRIVMSG", tags={})

        self.assertMessageMatch(m, command="PRIVMSG", tags={"label": "12345"})

    @pytest.mark.react_tag
    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledPrivmsgResponsesToChannel(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response"],
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
        self.assertMessageMatch(mt, command="PRIVMSG", tags={})

        # ensure sender correctly receives msg
        self.assertMessageMatch(ms, command="PRIVMSG", tags={"label": "12345"})

    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledPrivmsgResponsesToSelf(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
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

    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledNoticeResponsesToClient(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        self.sendLine(1, "@label=12345 NOTICE bar :hi")
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(m2, command="NOTICE", tags={})

        self.assertMessageMatch(m, command="NOTICE", tags={"label": "12345"})

    @pytest.mark.react_tag
    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledNoticeResponsesToChannel(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response"],
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
        self.assertMessageMatch(mt, command="NOTICE", tags={})

        # ensure sender correctly receives msg
        self.assertMessageMatch(ms, command="NOTICE", tags={"label": "12345"})

    @cases.mark_capabilities("echo-message", "batch", "labeled-response")
    def testLabeledNoticeResponsesToSelf(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response"],
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

    @pytest.mark.react_tag
    @cases.mark_capabilities(
        "echo-message", "batch", "labeled-response", "message-tags"
    )
    def testLabeledTagMsgResponsesToClient(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        # Need to get a valid msgid because Unreal validates them
        self.sendLine(1, "PRIVMSG bar :hi")
        msgid = self.getMessage(1).tags["msgid"]
        assert msgid == self.getMessage(2).tags["msgid"]

        self.sendLine(
            1, f"@label=12345;+draft/reply={msgid};+draft/react=l😃l TAGMSG bar"
        )
        m = self.getMessage(1)
        m2 = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            m2,
            command="TAGMSG",
            tags={
                "+draft/reply": msgid,
                "+draft/react": "l😃l",
                RemainingKeys(NotStrRe("label")): ANYOPTSTR,
            },
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

        self.assertMessageMatch(
            m,
            command="TAGMSG",
            tags={
                "label": "12345",
                "+draft/reply": msgid,
                "+draft/react": "l😃l",
                **ANYDICT,
            },
        )

    @pytest.mark.react_tag
    @cases.mark_capabilities(
        "echo-message", "batch", "labeled-response", "message-tags"
    )
    def testLabeledTagMsgResponsesToChannel(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(1)
        self.connectClient(
            "bar",
            capabilities=["echo-message", "batch", "labeled-response", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(2)

        # join channels
        self.sendLine(1, "JOIN #test")
        self.getMessages(1)
        self.sendLine(2, "JOIN #test")
        self.getMessages(2)
        self.getMessages(1)

        # Need to get a valid msgid because Unreal validates them
        self.sendLine(1, "PRIVMSG #test :hi")
        msgid = self.getMessage(1).tags["msgid"]
        assert msgid == self.getMessage(2).tags["msgid"]

        self.sendLine(
            1, f"@label=12345;+draft/reply={msgid};+draft/react=l😃l TAGMSG #test"
        )
        ms = self.getMessage(1)
        mt = self.getMessage(2)

        # ensure the label isn't sent to recipient
        self.assertMessageMatch(
            mt,
            command="TAGMSG",
            tags={
                "+draft/reply": msgid,
                "+draft/react": "l😃l",
                RemainingKeys(NotStrRe("label")): ANYOPTSTR,
            },
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
            ms,
            command="TAGMSG",
            tags={"label": "12345", "+draft/reply": msgid, **ANYDICT},
        )

    @pytest.mark.react_tag
    @cases.mark_capabilities(
        "echo-message", "batch", "labeled-response", "message-tags"
    )
    def testLabeledTagMsgResponsesToSelf(self):
        self.connectClient(
            "foo",
            capabilities=["echo-message", "batch", "labeled-response", "message-tags"],
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
            "bar", capabilities=["batch", "labeled-response"], skip_if_cap_nak=True
        )
        self.getMessages(1)

        self.sendLine(1, "@label=98765 PING adhoctestline")
        # no BATCH should be initiated for a one-line response,
        # it should just be labeled
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="PONG", tags={"label": "98765"})
        self.assertEqual(m.params[-1], "adhoctestline")

    @cases.mark_capabilities("labeled-response")
    def testEmptyBatchForNoResponse(self):
        self.connectClient(
            "bar", capabilities=["batch", "labeled-response"], skip_if_cap_nak=True
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

        self.assertMessageMatch(ack, command="ACK", tags={"label": "98765"})

    @cases.mark_capabilities("labeled-response")
    def testUnknownCommand(self):
        self.connectClient(
            "bar", capabilities=["batch", "labeled-response"], skip_if_cap_nak=True
        )

        # this command doesn't exist, but the error response should still
        # be labeled:
        self.sendLine(1, "@label=deadbeef NONEXISTENT_COMMAND")
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        unknowncommand = ms[0]
        self.assertMessageMatch(
            unknowncommand, command=ERR_UNKNOWNCOMMAND, tags={"label": "deadbeef"}
        )
