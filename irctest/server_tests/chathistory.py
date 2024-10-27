"""
`IRCv3 draft chathistory <https://ircv3.net/specs/extensions/chathistory>`_
"""

import dataclasses
import functools
import secrets
import time

import pytest

from irctest import cases, runner
from irctest.irc_utils.junkdrawer import random_name
from irctest.patma import ANYSTR, StrRe

CHATHISTORY_CAP = "draft/chathistory"
EVENT_PLAYBACK_CAP = "draft/event-playback"

# Keep this in sync with validate_chathistory()
SUBCOMMANDS = ["LATEST", "BEFORE", "AFTER", "BETWEEN", "AROUND"]

MYSQL_PASSWORD = ""


def skip_ngircd(f):
    @functools.wraps(f)
    def newf(self, *args, **kwargs):
        if self.controller.software_name == "ngIRCd":
            raise runner.OptionalExtensionNotSupported("nicks longer 9 characters")
        return f(self, *args, **kwargs)

    return newf


class _BaseChathistoryTests(cases.BaseServerTestCase):
    def _wait_before_chathistory(self):
        """Hook for the Sable-specific tests that check the postgresql-based
        CHATHISTORY implementation is sound. This implementation only kicks in
        after the in-memory history is cleared, which happens after a 5 min timeout;
        and this gives a chance to :class:``SablePostgresqlHistoryTestCase`` to
        wait this timeout.

        For other tests, this does nothing.
        """
        raise NotImplementedError("_BaseChathistoryTests._wait_before_chathistory")

    def validate_chathistory_batch(self, user, target):
        # may need to try again for Sable, as it has a pretty high latency here
        while not (msgs := self.getMessages(user)):
            pass
        (start, *inner_msgs, end) = msgs

        self.assertMessageMatch(
            start, command="BATCH", params=[StrRe(r"\+.*"), "chathistory", target]
        )
        batch_tag = start.params[0][1:]
        self.assertMessageMatch(end, command="BATCH", params=["-" + batch_tag])

        result = []
        for msg in inner_msgs:
            if (
                msg.command in ("PRIVMSG", "TOPIC")
                and batch_tag is not None
                and msg.tags.get("batch") == batch_tag
            ):
                if not msg.prefix.startswith("HistServ!"):  # FIXME: ergo-specific
                    result.append(msg.to_history_message())
        return result

    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(chathistory=True)

    def _supports_msgid(self):
        return "msgid" in self.server_support.get(
            "MSGREFTYPES", "msgid,timestamp"
        ).split(",")

    def _supports_timestamp(self):
        return "timestamp" in self.server_support.get(
            "MSGREFTYPES", "msgid,timestamp"
        ).split(",")

    @skip_ngircd
    def testInvalidTargets(self):
        bar, pw = random_name("bar"), random_name("pw")
        self.controller.registerUser(self, bar, pw)
        self.connectClient(
            bar,
            name=bar,
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password=pw,
            skip_if_cap_nak=True,
        )
        self.getMessages(bar)

        qux = random_name("qux")
        real_chname = random_name("#real_channel")
        self.connectClient(qux, name=qux)
        self.joinChannel(qux, real_chname)
        self.getMessages(qux)

        self._wait_before_chathistory()

        # test a nonexistent channel
        self.sendLine(bar, "CHATHISTORY LATEST #nonexistent_channel * 10")
        msgs = self.getMessages(bar)
        msgs = [msg for msg in msgs if msg.command != "MODE"]  # :NickServ MODE +r
        self.assertMessageMatch(
            msgs[0],
            command="FAIL",
            params=["CHATHISTORY", "INVALID_TARGET", "LATEST", ANYSTR, ANYSTR],
        )

        # as should a real channel to which one is not joined:
        self.sendLine(bar, "CHATHISTORY LATEST %s * 10" % (real_chname,))
        msgs = self.getMessages(bar)
        self.assertMessageMatch(
            msgs[0],
            command="FAIL",
            params=["CHATHISTORY", "INVALID_TARGET", "LATEST", ANYSTR, ANYSTR],
        )

    @pytest.mark.private_chathistory
    @skip_ngircd
    def testMessagesToSelf(self):
        bar, pw = random_name("bar"), random_name("pw")
        self.controller.registerUser(self, bar, pw)
        self.connectClient(
            bar,
            name=bar,
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "sasl",
                "server-time",
                CHATHISTORY_CAP,
            ],
            password=pw,
            skip_if_cap_nak=True,
        )
        self.getMessages(bar)

        messages = []

        self.sendLine(bar, "PRIVMSG %s :this is a privmsg sent to myself" % (bar,))
        replies = [msg for msg in self.getMessages(bar) if msg.command == "PRIVMSG"]
        self.assertEqual(len(replies), 1)
        msg = replies[0]
        self.assertMessageMatch(msg, params=[bar, "this is a privmsg sent to myself"])
        messages.append(msg.to_history_message())

        self.sendLine(bar, "CAP REQ echo-message")
        self.getMessages(bar)
        self.sendLine(
            bar, "PRIVMSG %s :this is a second privmsg sent to myself" % (bar,)
        )
        replies = [msg for msg in self.getMessages(bar) if msg.command == "PRIVMSG"]
        # two messages, the echo and the delivery
        self.assertEqual(len(replies), 2)
        self.assertMessageMatch(
            replies[0], params=[bar, "this is a second privmsg sent to myself"]
        )
        messages.append(replies[0].to_history_message())
        # messages should be otherwise identical
        self.assertEqual(
            replies[0].to_history_message(), replies[1].to_history_message()
        )

        self.sendLine(
            bar,
            "@label=xyz PRIVMSG %s :this is a third privmsg sent to myself" % (bar,),
        )
        replies = [msg for msg in self.getMessages(bar) if msg.command == "PRIVMSG"]
        self.assertEqual(len(replies), 2)
        # exactly one of the replies MUST be labeled
        echo = [msg for msg in replies if msg.tags.get("label") == "xyz"][0]
        delivery = [msg for msg in replies if msg.tags.get("label") is None][0]
        self.assertMessageMatch(
            echo, params=[bar, "this is a third privmsg sent to myself"]
        )
        messages.append(echo.to_history_message())
        self.assertEqual(echo.to_history_message(), delivery.to_history_message())

        self._wait_before_chathistory()

        self.sendLine(bar, "CHATHISTORY LATEST %s * 10" % (bar,))
        replies = [msg for msg in self.getMessages(bar) if msg.command == "PRIVMSG"]
        self.assertEqual([msg.to_history_message() for msg in replies], messages)

    def validate_echo_messages(self, num_messages, echo_messages):
        # sanity checks: should have received the correct number of echo messages,
        # all with distinct time tags (because we slept) and msgids
        self.assertEqual(len(echo_messages), num_messages)
        self.assertEqual(len(set(msg.msgid for msg in echo_messages)), num_messages)
        self.assertEqual(len(set(msg.time for msg in echo_messages)), num_messages)

    @pytest.mark.parametrize("subcommand", SUBCOMMANDS)
    @skip_ngircd
    def testChathistory(self, subcommand):
        if subcommand == "BETWEEN" and self.controller.software_name == "UnrealIRCd":
            pytest.xfail(
                "CHATHISTORY BETWEEN does not apply bounds correct "
                "https://bugs.unrealircd.org/view.php?id=5952"
            )
        if subcommand == "AROUND" and self.controller.software_name == "UnrealIRCd":
            pytest.xfail(
                "CHATHISTORY AROUND excludes 'central' messages "
                "https://bugs.unrealircd.org/view.php?id=5953"
            )

        self.connectClient(
            "bar",
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            skip_if_cap_nak=True,
        )
        chname = "#chan" + secrets.token_hex(12)
        self.joinChannel(1, chname)
        self.getMessages(1)
        self.getMessages(1)

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            self.sendLine(1, "PRIVMSG %s :this is message %d" % (chname, i))
            echo_messages.extend(
                msg.to_history_message() for msg in self.getMessages(1)
            )
            time.sleep(0.02)

        self.validate_echo_messages(NUM_MESSAGES, echo_messages)

        self._wait_before_chathistory()

        self.validate_chathistory(subcommand, echo_messages, 1, chname)

    @skip_ngircd
    def testChathistoryNoEventPlayback(self):
        """Tests that non-messages don't appear in the chat history when event-playback
        is not enabled."""

        self.connectClient(
            "bar",
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            skip_if_cap_nak=True,
        )
        chname = "#chan" + secrets.token_hex(12)
        self.joinChannel(1, chname)
        self.getMessages(1)
        self.getMessages(1)

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            self.sendLine(1, "TOPIC %s :this is topic %d" % (chname, i))
            self.getMessages(1)
            self.sendLine(1, "PRIVMSG %s :this is message %d" % (chname, i))
            echo_messages.extend(
                msg.to_history_message() for msg in self.getMessages(1)
            )
            time.sleep(0.002)

        self._wait_before_chathistory()

        self.validate_echo_messages(NUM_MESSAGES, echo_messages)
        self.sendLine(1, "CHATHISTORY LATEST %s * 100" % chname)
        (batch_open, *messages, batch_close) = self.getMessages(1)
        self.assertMessageMatch(batch_open, command="BATCH")
        self.assertMessageMatch(batch_close, command="BATCH")
        self.assertEqual([msg for msg in messages if msg.command != "PRIVMSG"], [])

    @pytest.mark.parametrize("subcommand", SUBCOMMANDS)
    @skip_ngircd
    def testChathistoryEventPlayback(self, subcommand):
        self.connectClient(
            "bar",
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
                EVENT_PLAYBACK_CAP,
            ],
            skip_if_cap_nak=True,
        )
        chname = "#chan" + secrets.token_hex(12)
        self.joinChannel(1, chname)
        self.getMessages(1)

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            self.sendLine(1, "TOPIC %s :this is topic %d" % (chname, i))
            echo_messages.extend(
                msg.to_history_message() for msg in self.getMessages(1)
            )
            time.sleep(0.002)

            self.sendLine(1, "PRIVMSG %s :this is message %d" % (chname, i))
            echo_messages.extend(
                msg.to_history_message() for msg in self.getMessages(1)
            )
            time.sleep(0.002)

        self.validate_echo_messages(NUM_MESSAGES * 2, echo_messages)

        self._wait_before_chathistory()

        self.validate_chathistory(subcommand, echo_messages, 1, chname)

    @pytest.mark.parametrize("subcommand", SUBCOMMANDS)
    @pytest.mark.private_chathistory
    @skip_ngircd
    def testChathistoryDMs(self, subcommand):
        c1 = random_name("foo")
        c2 = random_name("bar")
        self.controller.registerUser(self, c1, "sesame1")
        self.controller.registerUser(self, c2, "sesame2")
        self.connectClient(
            c1,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password="sesame1",
            skip_if_cap_nak=True,
        )
        self.connectClient(
            c2,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password="sesame2",
        )
        self.getMessages(1)
        self.getMessages(2)

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            user = (i % 2) + 1
            if user == 1:
                target = c2
            else:
                target = c1
            self.getMessages(user)
            self.sendLine(user, "PRIVMSG %s :this is message %d" % (target, i))
            echo_messages.extend(
                msg.to_history_message() for msg in self.getMessages(user)
            )
            time.sleep(0.002)

        self.getMessages(1)
        self.getMessages(2)

        self.validate_echo_messages(NUM_MESSAGES, echo_messages)

        self._wait_before_chathistory()

        self.validate_chathistory(subcommand, echo_messages, 1, c2)
        self.validate_chathistory(subcommand, echo_messages, 2, c1)

        c3 = random_name("baz")
        self.connectClient(
            c3,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                CHATHISTORY_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.sendLine(
            1, "PRIVMSG %s :this is a message in a separate conversation" % (c3,)
        )
        self.getMessages(1)
        self.sendLine(
            3, "PRIVMSG %s :i agree that this is a separate conversation" % (c1,)
        )
        # 3 received the first message as a delivery and the second as an echo
        new_convo = [
            msg.to_history_message()
            for msg in self.getMessages(3)
            if msg.command == "PRIVMSG"
        ]
        self.assertEqual(
            [msg.text for msg in new_convo],
            [
                "this is a message in a separate conversation",
                "i agree that this is a separate conversation",
            ],
        )

        # messages should be stored and retrievable by c1,
        # even though c3 is not registered
        self.getMessages(1)
        self.sendLine(1, "CHATHISTORY LATEST %s * 10" % (c3,))
        results = [
            msg.to_history_message()
            for msg in self.getMessages(1)
            if msg.command == "PRIVMSG"
        ]
        self.assertEqual(results, new_convo)

        self._wait_before_chathistory()

        # additional messages with c3 should not show up in the c1-c2 history:
        self.validate_chathistory(subcommand, echo_messages, 1, c2)
        self.validate_chathistory(subcommand, echo_messages, 2, c1)
        self.validate_chathistory(subcommand, echo_messages, 2, c1.upper())

        # regression test for #833
        self.sendLine(3, "QUIT")
        self.assertDisconnected(3)
        # register c3 as an account, then attempt to retrieve
        # the conversation history with c1
        self.controller.registerUser(self, c3, "sesame3")
        self.connectClient(
            c3,
            name=c3,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password="sesame3",
            skip_if_cap_nak=True,
        )
        self.getMessages(c3)
        self.sendLine(c3, "CHATHISTORY LATEST %s * 10" % (c1,))
        results = [
            msg.to_history_message()
            for msg in self.getMessages(c3)
            if msg.command == "PRIVMSG"
        ]
        # should get nothing
        self.assertEqual(results, [])

    def validate_chathistory(self, subcommand, echo_messages, user, chname):
        # Keep this list of subcommands in sync with the SUBCOMMANDS global
        method = getattr(self, f"_validate_chathistory_{subcommand}")
        method(echo_messages, user, chname)

    def _validate_chathistory_LATEST(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2
        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, INCLUSIVE_LIMIT))
        result = self.validate_chathistory_batch(user, chname)
        self.assertEqual(echo_messages, result)

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, 5))
        result = self.validate_chathistory_batch(user, chname)
        self.assertEqual(echo_messages[-5:], result)

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, 1))
        result = self.validate_chathistory_batch(user, chname)
        self.assertEqual(echo_messages[-1:], result)

        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY LATEST %s msgid=%s %d"
                % (chname, echo_messages[4].msgid, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[5:], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY LATEST %s timestamp=%s %d"
                % (chname, echo_messages[4].time, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[5:], result)

    def _validate_chathistory_BEFORE(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2
        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY BEFORE %s msgid=%s %d"
                % (chname, echo_messages[6].msgid, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[:6], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY BEFORE %s timestamp=%s %d"
                % (chname, echo_messages[6].time, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[:6], result)

            self.sendLine(
                user,
                "CHATHISTORY BEFORE %s timestamp=%s %d"
                % (chname, echo_messages[6].time, 2),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[4:6], result)

    def _validate_chathistory_AFTER(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2
        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY AFTER %s msgid=%s %d"
                % (chname, echo_messages[3].msgid, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[4:], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY AFTER %s timestamp=%s %d"
                % (chname, echo_messages[3].time, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[4:], result)

            self.sendLine(
                user,
                "CHATHISTORY AFTER %s timestamp=%s %d"
                % (chname, echo_messages[3].time, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[4:7], result)

    def _validate_chathistory_BETWEEN(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2
        if self._supports_msgid():
            # BETWEEN forwards and backwards
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d"
                % (
                    chname,
                    echo_messages[0].msgid,
                    echo_messages[-1].msgid,
                    INCLUSIVE_LIMIT,
                ),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[1:-1], result)

            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d"
                % (
                    chname,
                    echo_messages[-1].msgid,
                    echo_messages[0].msgid,
                    INCLUSIVE_LIMIT,
                ),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[1:-1], result)

            # BETWEEN forwards and backwards with a limit, should get
            # different results this time
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d"
                % (chname, echo_messages[0].msgid, echo_messages[-1].msgid, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[1:4], result)

            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d"
                % (chname, echo_messages[-1].msgid, echo_messages[0].msgid, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[-4:-1], result)

        if self._supports_timestamp():
            # same stuff again but with timestamps
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d"
                % (
                    chname,
                    echo_messages[0].time,
                    echo_messages[-1].time,
                    INCLUSIVE_LIMIT,
                ),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[1:-1], result)
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d"
                % (
                    chname,
                    echo_messages[-1].time,
                    echo_messages[0].time,
                    INCLUSIVE_LIMIT,
                ),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[1:-1], result)
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d"
                % (chname, echo_messages[0].time, echo_messages[-1].time, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[1:4], result)
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d"
                % (chname, echo_messages[-1].time, echo_messages[0].time, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[-4:-1], result)

    def _validate_chathistory_AROUND(self, echo_messages, user, chname):
        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY AROUND %s msgid=%s %d"
                % (chname, echo_messages[7].msgid, 1),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual([echo_messages[7]], result)

            self.sendLine(
                user,
                "CHATHISTORY AROUND %s msgid=%s %d"
                % (chname, echo_messages[7].msgid, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertEqual(echo_messages[6:9], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY AROUND %s timestamp=%s %d"
                % (chname, echo_messages[7].time, 3),
            )
            result = self.validate_chathistory_batch(user, chname)
            self.assertIn(echo_messages[7], result)

    @pytest.mark.arbitrary_client_tags
    @skip_ngircd
    def testChathistoryTagmsg(self):
        c1 = random_name("foo")
        c2 = random_name("bar")
        chname = "#chan" + secrets.token_hex(12)
        self.controller.registerUser(self, c1, "sesame1")
        self.controller.registerUser(self, c2, "sesame2")
        self.connectClient(
            c1,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
                EVENT_PLAYBACK_CAP,
            ],
            password="sesame1",
            skip_if_cap_nak=True,
        )
        self.connectClient(
            c2,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password="sesame2",
        )
        self.joinChannel(1, chname)
        self.joinChannel(2, chname)
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(
            1, "@+client-only-tag-test=success;+draft/persist TAGMSG %s" % (chname,)
        )
        echo = self.getMessages(1)[0]
        msgid = echo.tags["msgid"]

        def validate_tagmsg(msg, target, msgid):
            self.assertMessageMatch(msg, command="TAGMSG", params=[target])
            self.assertEqual(msg.tags["+client-only-tag-test"], "success")
            self.assertEqual(msg.tags["msgid"], msgid)

        validate_tagmsg(echo, chname, msgid)

        relay = self.getMessages(2)
        self.assertEqual(len(relay), 1)
        validate_tagmsg(relay[0], chname, msgid)

        self._wait_before_chathistory()

        self.sendLine(1, "CHATHISTORY LATEST %s * 10" % (chname,))
        history_tagmsgs = [
            msg for msg in self.getMessages(1) if msg.command == "TAGMSG"
        ]
        self.assertEqual(len(history_tagmsgs), 1)
        validate_tagmsg(history_tagmsgs[0], chname, msgid)

        # c2 doesn't have event-playback and MUST NOT receive replayed tagmsg
        self.sendLine(2, "CHATHISTORY LATEST %s * 10" % (chname,))
        history_tagmsgs = [
            msg for msg in self.getMessages(2) if msg.command == "TAGMSG"
        ]
        self.assertEqual(len(history_tagmsgs), 0)

        # now try a DM
        self.sendLine(
            1, "@+client-only-tag-test=success;+draft/persist TAGMSG %s" % (c2,)
        )
        echo = self.getMessages(1)[0]
        msgid = echo.tags["msgid"]
        validate_tagmsg(echo, c2, msgid)

        relay = self.getMessages(2)
        self.assertEqual(len(relay), 1)
        validate_tagmsg(relay[0], c2, msgid)

        self.sendLine(1, "CHATHISTORY LATEST %s * 10" % (c2,))
        history_tagmsgs = [
            msg for msg in self.getMessages(1) if msg.command == "TAGMSG"
        ]
        self.assertEqual(len(history_tagmsgs), 1)
        validate_tagmsg(history_tagmsgs[0], c2, msgid)

        # c2 doesn't have event-playback and MUST NOT receive replayed tagmsg
        self.sendLine(2, "CHATHISTORY LATEST %s * 10" % (c1,))
        history_tagmsgs = [
            msg for msg in self.getMessages(2) if msg.command == "TAGMSG"
        ]
        self.assertEqual(len(history_tagmsgs), 0)

    @pytest.mark.arbitrary_client_tags
    @pytest.mark.private_chathistory
    @skip_ngircd
    def testChathistoryDMClientOnlyTags(self):
        # regression test for Ergo #1411
        c1 = random_name("foo")
        c2 = random_name("bar")
        self.controller.registerUser(self, c1, "sesame1")
        self.controller.registerUser(self, c2, "sesame2")
        self.connectClient(
            c1,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password="sesame1",
            skip_if_cap_nak=True,
        )
        self.connectClient(
            c2,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            password="sesame2",
        )
        self.getMessages(1)
        self.getMessages(2)

        echo_msgid = None

        def validate_msg(msg):
            self.assertMessageMatch(msg, command="PRIVMSG", params=[c2, "hi"])
            self.assertEqual(msg.tags["+client-only-tag-test"], "success")
            self.assertEqual(msg.tags["msgid"], echo_msgid)

        self.sendLine(
            1, "@+client-only-tag-test=success;+draft/persist PRIVMSG %s hi" % (c2,)
        )
        echo = self.getMessage(1)
        echo_msgid = echo.tags["msgid"]
        validate_msg(echo)
        relay = self.getMessage(2)
        validate_msg(relay)


@cases.mark_specifications("IRCv3")
@cases.mark_services
class ChathistoryTestCase(_BaseChathistoryTests):
    def _wait_before_chathistory(self):
        """does nothing"""
        pass


assert {f"_validate_chathistory_{cmd}" for cmd in SUBCOMMANDS} == {
    meth_name
    for meth_name in dir(ChathistoryTestCase)
    if meth_name.startswith("_validate_chathistory_")
}, "ChathistoryTestCase.validate_chathistory and SUBCOMMANDS are out of sync"


@cases.mark_specifications("Sable")
@cases.mark_services
class SablePostgresqlHistoryTestCase(_BaseChathistoryTests):
    # for every wall clock second, 10 seconds pass for the server.
    # At x15, sable_history does not always have time to persist messages (wtf?)
    # at x30, links between nodes timeout.
    faketime = "+1y x10"

    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return dataclasses.replace(  # type: ignore[no-any-return]
            _BaseChathistoryTests.config(),
            sable_history_server=True,
        )

    def _wait_before_chathistory(self):
        """waits 15 seconds which appears to be a 1.5 min to Sable; which goes over
        the 1 min timeout for in-memory history"""
        assert self.controller.faketime_enabled, "faketime is not installed"
        time.sleep(15)


@cases.mark_specifications("Sable")
@cases.mark_services
class SableExpiringHistoryTestCase(cases.BaseServerTestCase):
    faketime = "+1y x10"

    def _wait_before_chathistory(self):
        """waits 6 seconds which appears to be a 1.5 min to Sable; which goes over
        the 1 min timeout for in-memory history"""
        assert self.controller.faketime_enabled, "faketime is not installed"
        time.sleep(15)

    def testChathistoryExpired(self):
        """Checks that Sable forgets about messages if the history server is not available"""
        self.connectClient(
            "bar",
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "sasl",
                CHATHISTORY_CAP,
            ],
            skip_if_cap_nak=True,
        )
        chname = "#chan" + secrets.token_hex(12)
        self.joinChannel(1, chname)
        self.getMessages(1)
        self.getMessages(1)

        self.sendLine(1, f"PRIVMSG {chname} :this is a message")
        self.getMessages(1)

        self._wait_before_chathistory()

        self.sendLine(1, f"CHATHISTORY LATEST {chname} * 10")

        while not (messages := self.getMessages(1)):
            # Sable processes CHATHISTORY asynchronously, which can be pretty slow as it
            # sends cross-server requests. This means we can't just rely on a PING-PONG
            # or the usual time.sleep(self.controller.sync_sleep_time) to make sure
            # the ircd replied to us
            time.sleep(self.controller.sync_sleep_time)

        (start, *middle, end) = messages
        self.assertMessageMatch(
            start, command="BATCH", params=[StrRe(r"\+.*"), "chathistory", chname]
        )
        batch_tag = start.params[0][1:]
        self.assertMessageMatch(end, command="BATCH", params=["-" + batch_tag])
        self.assertEqual(
            len(middle), 0, f"Got messages that should be expired: {middle}"
        )
