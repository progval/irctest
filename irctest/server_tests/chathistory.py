"""
`IRCv3 draft chathistory <https://ircv3.net/specs/extensions/chathistory>`_
"""

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


def skip_ngircd(f):
    @functools.wraps(f)
    def newf(self, *args, **kwargs):
        if self.controller.software_name == "ngIRCd":
            raise runner.OptionalExtensionNotSupported("nicks longer 9 characters")
        return f(self, *args, **kwargs)

    return newf


@cases.mark_specifications("IRCv3")
@cases.mark_services
class ChathistoryTestCase(cases.BaseServerTestCase):
    def validate_chathistory_batch(self, msgs, target):
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
            time.sleep(0.002)

        self.validate_echo_messages(NUM_MESSAGES, echo_messages)
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
        result = self.validate_chathistory_batch(self.getMessages(user), chname)
        self.assertEqual(echo_messages, result)

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, 5))
        result = self.validate_chathistory_batch(self.getMessages(user), chname)
        self.assertEqual(echo_messages[-5:], result)

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, 1))
        result = self.validate_chathistory_batch(self.getMessages(user), chname)
        self.assertEqual(echo_messages[-1:], result)

        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY LATEST %s msgid=%s %d"
                % (chname, echo_messages[4].msgid, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[5:], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY LATEST %s timestamp=%s %d"
                % (chname, echo_messages[4].time, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[5:], result)

    def _validate_chathistory_BEFORE(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2
        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY BEFORE %s msgid=%s %d"
                % (chname, echo_messages[6].msgid, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[:6], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY BEFORE %s timestamp=%s %d"
                % (chname, echo_messages[6].time, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[:6], result)

            self.sendLine(
                user,
                "CHATHISTORY BEFORE %s timestamp=%s %d"
                % (chname, echo_messages[6].time, 2),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[4:6], result)

    def _validate_chathistory_AFTER(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2
        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY AFTER %s msgid=%s %d"
                % (chname, echo_messages[3].msgid, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[4:], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY AFTER %s timestamp=%s %d"
                % (chname, echo_messages[3].time, INCLUSIVE_LIMIT),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[4:], result)

            self.sendLine(
                user,
                "CHATHISTORY AFTER %s timestamp=%s %d"
                % (chname, echo_messages[3].time, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
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
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
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
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[1:-1], result)

            # BETWEEN forwards and backwards with a limit, should get
            # different results this time
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d"
                % (chname, echo_messages[0].msgid, echo_messages[-1].msgid, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[1:4], result)

            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d"
                % (chname, echo_messages[-1].msgid, echo_messages[0].msgid, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
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
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
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
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[1:-1], result)
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d"
                % (chname, echo_messages[0].time, echo_messages[-1].time, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[1:4], result)
            self.sendLine(
                user,
                "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d"
                % (chname, echo_messages[-1].time, echo_messages[0].time, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[-4:-1], result)

    def _validate_chathistory_AROUND(self, echo_messages, user, chname):
        if self._supports_msgid():
            self.sendLine(
                user,
                "CHATHISTORY AROUND %s msgid=%s %d"
                % (chname, echo_messages[7].msgid, 1),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual([echo_messages[7]], result)

            self.sendLine(
                user,
                "CHATHISTORY AROUND %s msgid=%s %d"
                % (chname, echo_messages[7].msgid, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
            self.assertEqual(echo_messages[6:9], result)

        if self._supports_timestamp():
            self.sendLine(
                user,
                "CHATHISTORY AROUND %s timestamp=%s %d"
                % (chname, echo_messages[7].time, 3),
            )
            result = self.validate_chathistory_batch(self.getMessages(user), chname)
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

    @pytest.mark.private_chathistory
    @skip_ngircd
    def testChathistoryTargets(self):
        """Tests the CHATHISTORY TARGETS command, which lists channels the user has visible
        history in and users with which the user has exchanged direct messages."""
        c1 = random_name("foo")
        c2 = random_name("bar")
        c3 = random_name("baz")

        # Register users
        self.controller.registerUser(self, c1, "sesame1")
        self.controller.registerUser(self, c2, "sesame2")
        self.controller.registerUser(self, c3, "sesame3")

        # Connect with all capabilities
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

        self.connectClient(
            c3,
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
        )

        # Clear any initial messages
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        # Create a few channels for testing
        ch1 = "#chan" + secrets.token_hex(8)
        ch2 = "#chan" + secrets.token_hex(8)

        # Join channels and exchange messages
        self.joinChannel(1, ch1)
        self.joinChannel(2, ch1)
        self.joinChannel(1, ch2)
        self.joinChannel(3, ch2)
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        target_times = {}  # Store target and their latest message times

        # Exchange messages between users and in channels
        # First, exchange messages in ch1
        self.sendLine(1, f"PRIVMSG {ch1} :Hello channel 1")
        self.getMessages(1)
        ch1_msg = self.getMessages(2)[0]
        target_times[ch1] = ch1_msg.tags.get("time", "")
        time.sleep(0.002)

        # Then, DM between c1 and c2
        self.sendLine(1, f"PRIVMSG {c2} :Hello user 2")
        self.getMessages(1)
        c2_msg = self.getMessages(2)[0]
        target_times[c2] = c2_msg.tags.get("time", "")
        time.sleep(0.002)

        # Then, messages in ch2
        self.sendLine(1, f"PRIVMSG {ch2} :Hello channel 2")
        self.getMessages(1)
        ch2_msg = self.getMessages(3)[0]
        target_times[ch2] = ch2_msg.tags.get("time", "")
        time.sleep(0.002)

        # Finally, DM between c1 and c3
        self.sendLine(1, f"PRIVMSG {c3} :Hello user 3")
        self.getMessages(1)
        c3_msg = self.getMessages(3)[0]
        target_times[c3] = c3_msg.tags.get("time", "")

        # Now test TARGETS command
        # Get a timestamp before all messages
        before_all = "timestamp=2020-01-01T00:00:00.000Z"
        # Get a timestamp after all messages
        after_all = "timestamp=2262-01-01T00:00:00.000Z"

        # Execute TARGETS command
        self.sendLine(1, f"CHATHISTORY TARGETS {before_all} {after_all} 100")

        # Verify response
        batch_messages = self.getMessages(1)

        targets_results = self.summarize_chathistory_targets(batch_messages)
        # Check that each target we messaged is in the results
        # Targets should be sorted by time of latest message (earliest first)
        expected_order = [ch1, c2, ch2, c3]
        expected_results = [(target, target_times[target]) for target in expected_order]
        self.assertEqual(targets_results, expected_results)

        # Test with a limit parameter
        self.sendLine(1, f"CHATHISTORY TARGETS {before_all} {after_all} 2")
        batch_messages = self.getMessages(1)

        # Extract targets again
        targets_results = self.summarize_chathistory_targets(batch_messages)

        # Should only get 2 targets due to limit
        self.assertEqual([t[0] for t in targets_results], [ch1, c2])

        # Test with timestamp range that excludes some targets
        # Get the timestamp from the first message in ch1
        ch1_time = target_times[ch1]
        # Send the command to get targets after this time
        self.sendLine(1, f"CHATHISTORY TARGETS timestamp={ch1_time} {after_all} 100")
        batch_messages = self.getMessages(1)

        # Should only get targets that had messages after ch1_time
        # That would be c2, ch2, and c3, but not ch1
        targets_results = self.summarize_chathistory_targets(batch_messages)
        self.assertEqual([t[0] for t in targets_results], [c2, ch2, c3])

        # test limits on both sides
        ch3_time = target_times[c3]
        self.sendLine(
            1, f"CHATHISTORY TARGETS timestamp={ch1_time} timestamp={ch3_time} 100"
        )
        batch_messages = self.getMessages(1)
        targets_results = self.summarize_chathistory_targets(batch_messages)
        self.assertEqual([t[0] for t in targets_results], [c2, ch2])

    @pytest.mark.private_chathistory
    @skip_ngircd
    def testChathistoryTargetsExcludesUpdatedTargets(self):
        """Tests that CHATHISTORY TARGETS does not match targets that have messages
        within the selection window, but where the latest message is outside the
        selection window."""
        c1 = random_name("foo")

        # Register users
        self.controller.registerUser(self, c1, "sesame1")

        # Connect with all capabilities
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

        # Clear any initial messages
        self.getMessages(1)

        # Create a few channels for testing
        ch1 = "#chan" + secrets.token_hex(8)

        # Join channels and exchange messages
        self.joinChannel(1, ch1)
        self.getMessages(1)

        target_times = []

        for i in range(3):
            self.sendLine(1, f"PRIVMSG {ch1} :Hello channel {i}")
            ch1_msg = self.getMessages(1)[0]
            target_times.append(ch1_msg.tags["time"])
            time.sleep(0.002)

        # Now test TARGETS command
        # Get a timestamp before all messages
        before_all = "timestamp=2020-01-01T00:00:00.000Z"
        # Get a timestamp after all messages
        after_all = "timestamp=2262-01-01T00:00:00.000Z"

        # Execute TARGETS command
        self.sendLine(1, f"CHATHISTORY TARGETS {before_all} {after_all} 100")
        # Verify response
        batch_messages = self.getMessages(1)
        targets_results = self.summarize_chathistory_targets(batch_messages)
        expected_results = [(ch1, target_times[2])]
        self.assertEqual(targets_results, expected_results)

        # Execute TARGETS command with a time window excluding the latest message
        self.sendLine(
            1, f"CHATHISTORY TARGETS {before_all} timestamp={target_times[1]} 100"
        )
        # Verify response
        batch_messages = self.getMessages(1)
        targets_results = self.summarize_chathistory_targets(batch_messages)
        # should not receive any targets
        self.assertEqual(targets_results, [])

    def summarize_chathistory_targets(self, batch_messages):
        # Validate batch format
        batch_start = batch_messages[0]
        batch_end = batch_messages[-1]
        self.assertMessageMatch(
            batch_start,
            command="BATCH",
            params=[StrRe(r"\+.*"), "draft/chathistory-targets"],
        )
        batch_tag = batch_start.params[0][1:]
        self.assertMessageMatch(batch_end, command="BATCH", params=["-" + batch_tag])
        # Extract actual targets from the batch
        targets_results = []
        for msg in batch_messages:
            if (
                msg.command == "CHATHISTORY"
                and msg.params[0] == "TARGETS"
                and len(msg.params) >= 3
            ):
                targets_results.append((msg.params[1], msg.params[2]))
        return targets_results


assert {f"_validate_chathistory_{cmd}" for cmd in SUBCOMMANDS} == {
    meth_name
    for meth_name in dir(ChathistoryTestCase)
    if meth_name.startswith("_validate_chathistory_")
}, "ChathistoryTestCase.validate_chathistory and SUBCOMMANDS are out of sync"
