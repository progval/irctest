"""
`IRCv3 draft message redaction <https://github.com/progval/ircv3-specifications/blob/redaction/extensions/message-redaction.md>`_
"""

import uuid

import pytest

from irctest import cases
from irctest.patma import ANYDICT, ANYSTR, StrRe

CAPABILITIES = [
    "message-tags",
    "echo-message",
    "batch",
    "server-time",
    "labeled-response",
    "draft/message-redaction",
]


@cases.mark_specifications("IRCv3")
@cases.mark_capabilities(*CAPABILITIES)
class ChannelRedactTestCase(cases.BaseServerTestCase):
    def _setupRedactTest(self, redacteeId, redacteeNick, chathistory=False):
        capabilities = list(CAPABILITIES)
        if chathistory:
            capabilities.extend(["batch", "draft/chathistory"])
        self.connectClient("chanop", capabilities=capabilities, skip_if_cap_nak=True)
        self.sendLine(1, "JOIN #chan")
        self.connectClient("user", capabilities=capabilities, skip_if_cap_nak=True)
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)  # synchronize
        self.getMessages(1)

        self.sendLine(redacteeId, "@label=1234 PRIVMSG #chan :hello there")
        echo = self.getMessage(redacteeId)
        self.assertMessageMatch(
            echo,
            tags={"label": "1234", "msgid": StrRe("[^ ]+"), **ANYDICT},
            prefix=StrRe(redacteeNick + "!.*"),
            command="PRIVMSG",
            params=["#chan", "hello there"],
        )
        msgid = echo.tags["msgid"]

        self.assertMessageMatch(
            self.getMessage(3 - redacteeId),
            tags={"msgid": msgid, **ANYDICT},
            prefix=StrRe(redacteeNick + "!.*"),
            command="PRIVMSG",
            params=["#chan", "hello there"],
        )

        return msgid

    def testRelayOpSelfRedact(self):
        """Channel op writes a message and redacts it themselves."""
        msgid = self._setupRedactTest(redacteeId=1, redacteeNick="chanop")

        self.sendLine(1, f"REDACT #chan {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "oops"],
        )

        self.assertMessageMatch(
            self.getMessage(2),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "oops"],
        )

    def testRelayOpRedact(self):
        """User writes a message and channel op redacts it."""
        msgid = self._setupRedactTest(
            redacteeId=2,
            redacteeNick="user",
        )

        self.sendLine(1, f"REDACT #chan {msgid} :spam")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "spam"],
        )

        self.assertMessageMatch(
            self.getMessage(2),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "spam"],
        )

    def testRelayUserSelfRedact(self):
        """User writes a message and redacts it themselves.

        Servers may either accept or reject this."""
        msgid = self._setupRedactTest(redacteeId=2, redacteeNick="user")

        self.sendLine(2, f"REDACT #chan {msgid} :oops")

        msg = self.getMessage(2)
        if msg.command == "REDACT":
            self.assertMessageMatch(
                msg,
                prefix=StrRe("user!.*"),
                command="REDACT",
                params=["#chan", msgid, "oops"],
            )

            self.assertMessageMatch(
                self.getMessage(1),
                prefix=StrRe("user!.*"),
                command="REDACT",
                params=["#chan", msgid, "oops"],
            )
        else:
            self.assertMessageMatch(
                msg,
                command="FAIL",
                params=["REDACT", "REDACT_FORBIDDEN", "#chan", msgid, ANYSTR],
            )

            self.assertEqual(self.getMessages(1), [])

    def testRejectRedactOtherUser(self):
        """Channel op writes a message and a user attempts to redact it."""
        msgid = self._setupRedactTest(redacteeId=1, redacteeNick="chanop")

        self.sendLine(2, f"REDACT #chan {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(2),
            command="FAIL",
            params=["REDACT", "REDACT_FORBIDDEN", "#chan", msgid, ANYSTR],
        )

        self.assertEqual(self.getMessages(1), [])

    @pytest.mark.parametrize(
        "chathistory_requester",
        [
            pytest.param(1, id="chathistory-to-chanop"),
            pytest.param(2, id="chathistory-to-user"),
        ],
    )
    def testOpSelfRedactChathistory(self, chathistory_requester):
        """Channel op writes a message and redacts it themselves; both the op
        and a regular user check the chathistory afterward.

        https://github.com/progval/ircv3-specifications/blob/redaction/extensions/message-redaction.md#chat-history
        """
        msgid = self._setupRedactTest(
            redacteeId=1, redacteeNick="chanop", chathistory=True
        )

        self.sendLine(1, f"REDACT #chan {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "oops"],
        )

        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(chathistory_requester, "CHATHISTORY LATEST #chan * 10")

        (start_msg, *msgs, end_msg) = self.getMessages(chathistory_requester)
        self.assertMessageMatch(
            start_msg,
            command="BATCH",
            params=[StrRe(r"\+.+"), "chathistory", "#chan"],
        )
        batch_tag = start_msg.params[0][1:]

        # remove Ergo's event-playback fallback
        msgs = [msg for msg in msgs if not msg.prefix.startswith("HistServ!")]

        self.assertMessageMatch(end_msg, command="BATCH", params=["-" + batch_tag])

        if len(msgs) == 0:
            pass  # Server removed the message entirely
        elif len(msgs) == 1:
            # Server replaced with the REDACT
            self.assertMessageMatch(
                msgs[0],
                prefix=StrRe("sender!.*"),
                command="REDACT",
                params=["#chan", msgid, "oops"],
            )
        elif len(msgs) == 2:
            # Server appended the REDACT
            self.assertMessageMatch(
                msgs[0],
                tags={"msgid": msgid, **ANYDICT},
                command="PRIVMSG",
                params=["#chan", msgid, "hello there"],
            )
            self.assertMessageMatch(
                msgs[1],
                prefix=StrRe("sender!.*"),
                command="REDACT",
                params=["#chan", msgid, "oops"],
            )
        else:
            self.assertTrue(False, fail_msg=f"Unexpectedly many messages: {msgs}")

    def testOpRedactNonExistant(self):
        """Channel op writes a message and redacts a random non-existant id."""
        self._setupRedactTest(redacteeId=1, redacteeNick="chanop")

        nonexistent_msgid = str(uuid.uuid4())

        self.sendLine(1, f"REDACT #chan {nonexistent_msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["REDACT", "UNKNOWN_MSGID", "#chan", nonexistent_msgid, ANYSTR],
        )

        self.assertEqual(self.getMessages(2), [])

    def testOpRedactWrongChan(self):
        """Channel op writes a message and redacts it, but uses the wrong channel
        as target."""
        msgid = self._setupRedactTest(redacteeId=1, redacteeNick="chanop")

        self.sendLine(1, "JOIN #otherChan")
        self.getMessages(1)

        self.sendLine(1, f"REDACT #otherChan {msgid} :oops")

        msg = self.getMessage(1)

        self.assertMessageMatch(
            msg,
            command="FAIL",
        )
        if msg.params[1] == "UNKNOWN_MSGID":
            self.assertMessageMatch(
                msg,
                command="FAIL",
                params=["REDACT", "UNKNOWN_MSGID", "#otherChan", msgid, ANYSTR],
            )
        else:
            self.assertMessageMatch(
                msg,
                command="FAIL",
                params=["REDACT", "REDACT_FORBIDDEN", "#otherChan", ANYSTR],
            )

        self.assertEqual(self.getMessages(2), [])


@cases.mark_specifications("IRCv3")
@cases.mark_capabilities(*CAPABILITIES)
@cases.mark_services
@pytest.mark.private_chathistory
class PmRedactTestCase(cases.BaseServerTestCase):
    """Tests REDACT command in private messages between authenticated accounts"""

    def _setupRedactTest(self, chathistory=False):
        capabilities = [*CAPABILITIES, "sasl"]
        if chathistory:
            capabilities.extend(["batch", "draft/chathistory"])
        self.controller.registerUser(self, "sender", "senderpass")
        self.controller.registerUser(self, "recipient", "recipientpass")
        self.connectClient(
            "sender",
            password="senderpass",
            capabilities=capabilities,
            skip_if_cap_nak=True,
        )
        self.connectClient(
            "recipient",
            password="recipientpass",
            capabilities=capabilities,
            skip_if_cap_nak=True,
        )
        self.getMessages(2)  # synchronize
        self.getMessages(1)

        self.sendLine(1, "@label=1234 PRIVMSG recipient :hello there")
        echo = self.getMessage(1)
        self.assertMessageMatch(
            echo,
            tags={"label": "1234", "msgid": StrRe("[^ ]+"), **ANYDICT},
            prefix=StrRe("sender!.*"),
            command="PRIVMSG",
            params=["recipient", "hello there"],
        )
        msgid = echo.tags["msgid"]

        self.assertMessageMatch(
            self.getMessage(2),
            tags={"msgid": msgid, **ANYDICT},
            prefix=StrRe("sender!.*"),
            command="PRIVMSG",
            params=["recipient", "hello there"],
        )

        return msgid

    def testRelaySenderRedact(self):
        """Someone writes a message in private and redacts it themselves."""
        msgid = self._setupRedactTest()

        self.sendLine(1, f"REDACT recipient {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("sender!.*"),
            command="REDACT",
            params=["recipient", msgid, "oops"],
        )

        self.assertMessageMatch(
            self.getMessage(2),
            prefix=StrRe("sender!.*"),
            command="REDACT",
            params=["recipient", msgid, "oops"],
        )

    def testRelayRecipientRedact(self):
        """Someone writes a message in private and their recipient redacts it.

        Servers may either accept or reject this."""
        msgid = self._setupRedactTest()

        self.sendLine(2, f"REDACT sender {msgid} :oops")

        msg = self.getMessage(2)
        if msg.command == "REDACT":
            self.assertMessageMatch(
                msg,
                prefix=StrRe("recipient!.*"),
                command="REDACT",
                params=["sender", msgid, "oops"],
            )

            self.assertMessageMatch(
                self.getMessage(1),
                prefix=StrRe("user!.*"),
                command="REDACT",
                params=["sender", msgid, "oops"],
            )
        else:
            self.assertMessageMatch(
                msg,
                command="FAIL",
                params=[
                    "REDACT",
                    StrRe("(REDACT_FORBIDDEN|UNKNOWN_MSGID)"),
                    "sender",
                    msgid,
                    ANYSTR,
                ],
            )

            self.assertEqual(self.getMessages(1), [])

    @pytest.mark.parametrize("nick", ["sender", "recipient"])
    def testRejectRedactOtherUser(self, nick):
        """Someone writes a message in private to someone else and an unrelated person
        attempts to redact it."""
        msgid = self._setupRedactTest()

        self.controller.registerUser(self, "censor", "censorpass")
        self.connectClient(
            "censor",
            password="censorpass",
            capabilities=[*CAPABILITIES, "sasl"],
            skip_if_cap_nak=True,
        )
        self.getMessages(3)  # synchronize

        self.sendLine(3, f"REDACT {nick} {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(3),
            command="FAIL",
            params=[
                "REDACT",
                StrRe("(REDACT_FORBIDDEN|UNKNOWN_MSGID)"),
                nick,
                msgid,
                ANYSTR,
            ],
        )

        self.assertEqual(self.getMessages(1), [])
        self.assertEqual(self.getMessages(2), [])

    @pytest.mark.parametrize(
        "chathistory_requester",
        [
            pytest.param(1, id="chathistory-to-sender"),
            pytest.param(2, id="chathistory-to-recipient"),
        ],
    )
    @pytest.mark.private_chathistory
    def testSenderRedactChathistory(self, chathistory_requester):
        """Channel op writes a message and redacts it themselves; both the op
        and a regular user check the chathistory afterward.

        https://github.com/progval/ircv3-specifications/blob/redaction/extensions/message-redaction.md#chat-history
        """
        msgid = self._setupRedactTest(chathistory=True)

        self.sendLine(1, f"REDACT recipient {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("sender!.*"),
            command="REDACT",
            params=["recipient", msgid, "oops"],
        )

        self.getMessages(1)
        self.getMessages(2)

        if chathistory_requester == 1:
            others_nick = "recipient"
        else:
            others_nick = "sender"

        self.sendLine(chathistory_requester, f"CHATHISTORY LATEST {others_nick} * 10")

        (start_msg, *msgs, end_msg) = self.getMessages(chathistory_requester)
        self.assertMessageMatch(
            start_msg,
            command="BATCH",
            params=[StrRe(r"\+.+"), "chathistory", others_nick],
        )
        batch_tag = start_msg.params[0][1:]

        # remove Ergo's event-playback fallback
        msgs = [msg for msg in msgs if not msg.prefix.startswith("HistServ!")]

        self.assertMessageMatch(end_msg, command="BATCH", params=["-" + batch_tag])

        if len(msgs) == 0:
            pass  # Server removed the message entirely
        elif len(msgs) == 1:
            # Server replaced with the REDACT
            self.assertMessageMatch(
                msgs[0],
                prefix=StrRe("sender!.*"),
                command="REDACT",
                params=["recipient", msgid, "oops"],
            )
        elif len(msgs) == 2:
            # Server appended the REDACT
            self.assertMessageMatch(
                msgs[0],
                tags={"msgid": msgid, **ANYDICT},
                command="PRIVMSG",
                params=["recipient", msgid, "hello there"],
            )
            self.assertMessageMatch(
                msgs[1],
                prefix=StrRe("sender!.*"),
                command="REDACT",
                params=["recipient", msgid, "oops"],
            )
        else:
            self.assertTrue(False, fail_msg=f"Unexpectedly many messages: {msgs}")

    def testRedactNonExistant(self):
        """Someone writes a message in private to someone else and redacts a random
        non-existant id."""
        self._setupRedactTest()

        nonexistent_msgid = str(uuid.uuid4())

        self.sendLine(1, f"REDACT recipient {nonexistent_msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["REDACT", "UNKNOWN_MSGID", "recipient", nonexistent_msgid, ANYSTR],
        )

        self.assertEqual(self.getMessages(2), [])

    def testOpRedactWrongChan(self):
        """Channel op writes a message and redacts it, but uses the wrong channel
        as target."""
        msgid = self._setupRedactTest()

        self.sendLine(1, "JOIN #otherChan")
        self.getMessages(1)

        self.sendLine(1, f"REDACT #otherChan {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["REDACT", "UNKNOWN_MSGID", "#otherChan", msgid, ANYSTR],
        )

        self.assertEqual(self.getMessages(2), [])
