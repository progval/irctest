"""
`Draft IRCv3 multiline <https://ircv3.net/specs/extensions/multiline>`_
"""

from irctest import cases
from irctest.patma import ANYDICT, ANYSTR, StrRe

CAP_NAME = "draft/multiline"
BATCH_TYPE = "draft/multiline"
CONCAT_TAG = "draft/multiline-concat"

base_caps = ["message-tags", "batch", "echo-message", "server-time", "labeled-response"]


class MultilineTestCase(cases.BaseServerTestCase):
    @cases.mark_capabilities("draft/multiline")
    def testBasic(self):
        self.connectClient(
            "alice", capabilities=(base_caps + [CAP_NAME]), skip_if_cap_nak=True
        )
        self.joinChannel(1, "#test")
        self.connectClient("bob", capabilities=(base_caps + [CAP_NAME]))
        self.joinChannel(2, "#test")
        self.connectClient("charlie", capabilities=base_caps)
        self.joinChannel(3, "#test")

        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        self.sendLine(1, "@label=xyz BATCH +123 %s #test" % (BATCH_TYPE,))
        self.sendLine(1, "@batch=123 PRIVMSG #test hello")
        self.sendLine(1, "@batch=123 PRIVMSG #test :#how is ")
        self.sendLine(1, "@batch=123;%s PRIVMSG #test :everyone?" % (CONCAT_TAG,))
        self.sendLine(1, "BATCH -123")

        echo = self.getMessages(1)
        batchStart, batchEnd = echo[0], echo[-1]
        self.assertMessageMatch(
            batchStart,
            command="BATCH",
            params=[StrRe(r"\+.*"), BATCH_TYPE, "#test"],
            tags={"label": "xyz", **ANYDICT},
        )
        self.assertEqual(batchStart.tags.get("label"), "xyz")
        self.assertMessageMatch(batchEnd, command="BATCH", params=[StrRe("-.*")])
        self.assertEqual(
            batchStart.params[0][1:],
            batchEnd.params[0][1:],
            fail_msg="batch start and end do not match",
        )
        msgid = batchStart.tags.get("msgid")
        time = batchStart.tags.get("time")
        assert msgid
        assert time
        privmsgs = echo[1:-1]
        for msg in privmsgs:
            self.assertMessageMatch(msg, command="PRIVMSG")
            self.assertNotIn("msgid", msg.tags)
            self.assertNotIn("time", msg.tags)
        self.assertIn(CONCAT_TAG, echo[3].tags)

        relay = self.getMessages(2)
        batchStart, batchEnd = relay[0], relay[-1]
        self.assertMessageMatch(
            batchStart, command="BATCH", params=[StrRe(r"\+.*"), BATCH_TYPE, "#test"]
        )
        batchTag = batchStart.params[0][1:]
        self.assertMessageMatch(batchEnd, command="BATCH", params=["-" + batchTag])
        self.assertEqual(batchStart.tags.get("msgid"), msgid)
        self.assertEqual(batchStart.tags.get("time"), time)
        privmsgs = relay[1:-1]
        for msg in privmsgs:
            self.assertMessageMatch(msg, command="PRIVMSG")
            self.assertNotIn("msgid", msg.tags)
            self.assertNotIn("time", msg.tags)
            self.assertEqual(msg.tags.get("batch"), batchTag)
        self.assertIn(CONCAT_TAG, relay[3].tags)

        fallback_relay = self.getMessages(3)
        relayed_fmsgids = []
        for msg in fallback_relay:
            self.assertMessageMatch(msg, command="PRIVMSG")
            relayed_fmsgids.append(msg.tags.get("msgid"))
            self.assertEqual(msg.tags.get("time"), time)
            self.assertNotIn(CONCAT_TAG, msg.tags)
        self.assertEqual(relayed_fmsgids, [msgid] + [None] * (len(fallback_relay) - 1))

    @cases.mark_capabilities("draft/multiline")
    def testBlankLines(self):
        self.connectClient(
            "alice", capabilities=(base_caps + [CAP_NAME]), skip_if_cap_nak=True
        )
        self.joinChannel(1, "#test")
        self.connectClient("bob", capabilities=(base_caps + [CAP_NAME]))
        self.joinChannel(2, "#test")
        self.connectClient("charlie", capabilities=base_caps)
        self.joinChannel(3, "#test")

        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        self.sendLine(
            1, "@label=xyz;+client-only-tag BATCH +123 %s #test" % (BATCH_TYPE,)
        )
        self.sendLine(1, "@batch=123 PRIVMSG #test :")
        self.sendLine(1, "@batch=123 PRIVMSG #test :#how is ")
        self.sendLine(1, "@batch=123;%s PRIVMSG #test :everyone?" % (CONCAT_TAG,))
        self.sendLine(1, "BATCH -123")
        self.getMessages(1)

        relay = self.getMessages(2)
        batch_start = relay[0]
        privmsgs = relay[1:-1]
        self.assertEqual(len(privmsgs), 3)
        self.assertMessageMatch(privmsgs[0], command="PRIVMSG", params=["#test", ""])
        self.assertMessageMatch(
            privmsgs[1], command="PRIVMSG", params=["#test", "#how is "]
        )
        self.assertMessageMatch(
            privmsgs[2], command="PRIVMSG", params=["#test", "everyone?"]
        )
        self.assertIn("+client-only-tag", batch_start.tags)
        msgid = batch_start.tags["msgid"]

        fallback_relay = self.getMessages(3)
        self.assertEqual(len(fallback_relay), 2)
        self.assertMessageMatch(
            fallback_relay[0], command="PRIVMSG", params=["#test", "#how is "]
        )
        self.assertMessageMatch(
            fallback_relay[1], command="PRIVMSG", params=["#test", "everyone?"]
        )
        self.assertIn("+client-only-tag", fallback_relay[0].tags)
        self.assertIn("+client-only-tag", fallback_relay[1].tags)
        self.assertEqual(fallback_relay[0].tags["msgid"], msgid)

    @cases.mark_capabilities("draft/multiline")
    def testErrors(self):
        self.connectClient(
            "alice", capabilities=(base_caps + [CAP_NAME]), skip_if_cap_nak=True
        )
        self.joinChannel(1, "#test")

        # invalid batch tag:
        self.sendLine(1, "BATCH +123 %s #test" % (BATCH_TYPE,))
        self.sendLine(1, "@batch=231 PRIVMSG #test :hi")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["BATCH", "MULTILINE_INVALID", ANYSTR],
        )

        # cannot send the concat tag with a blank message:
        self.sendLine(1, "BATCH +123 %s #test" % (BATCH_TYPE,))
        self.sendLine(1, "@batch=123 PRIVMSG #test :hi")
        self.sendLine(1, "@batch=123;%s PRIVMSG #test :" % (CONCAT_TAG,))
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["BATCH", "MULTILINE_INVALID", ANYSTR],
        )

    @cases.mark_specifications("Ergo")
    def testLimits(self):
        # this test is Ergo-specific for now because it hardcodes the same
        # line and byte limits as in the Ergo controller; we can generalize it
        # in future for other multiline implementations

        self.connectClient(
            "alice", capabilities=(base_caps + [CAP_NAME]), skip_if_cap_nak=False
        )
        self.joinChannel(1, "#test")

        # line limit exceeded
        self.sendLine(1, "BATCH +123 %s #test" % (BATCH_TYPE,))
        for i in range(33):
            self.sendLine(1, "@batch=123 PRIVMSG #test hi")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["BATCH", "MULTILINE_MAX_LINES", "32", ANYSTR],
        )

        # byte limit exceeded
        self.sendLine(1, "BATCH +234 %s #test" % (BATCH_TYPE,))
        for i in range(11):
            self.sendLine(1, "@batch=234 PRIVMSG #test " + ("x" * 400))
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["BATCH", "MULTILINE_MAX_BYTES", "4096", ANYSTR],
        )
