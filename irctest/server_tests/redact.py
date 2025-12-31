"""
`IRCv3 draft message-redaction
<https://ircv3.net/specs/extensions/message-redaction>`_
"""

import pytest

from irctest import cases
from irctest.irc_utils.junkdrawer import random_name
from irctest.patma import ANYSTR, StrRe
from irctest.specifications import Capabilities

REDACT_CAP = Capabilities.MESSAGE_REDACTION.value


class RedactTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(chathistory=True)

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactPrivmsg(self):
        """Test basic redaction of a PRIVMSG.

        Tests that:
        - Users can redact their own messages
        - Channel operators can redact other users' messages
        - Non-operators cannot redact other users' messages
        """
        alice = random_name("alice")
        bob = random_name("bob")
        channel = random_name("#channel")

        # Connect alice with redaction capability
        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        # Alice joins first and becomes channel operator
        self.joinChannel(alice, channel)
        self.getMessages(alice)

        # Connect bob with redaction capability
        self.connectClient(
            bob,
            name=bob,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
        )
        self.joinChannel(bob, channel)
        self.getMessages(alice)
        self.getMessages(bob)

        # Alice sends a message and redacts her own message
        self.sendLine(alice, f"PRIVMSG {channel} :Hello everyone")
        alice_echo = self.getMessage(alice)
        bob_delivery = self.getMessage(bob)

        self.assertMessageMatch(
            alice_echo, command="PRIVMSG", params=[channel, "Hello everyone"]
        )
        self.assertMessageMatch(
            bob_delivery, command="PRIVMSG", params=[channel, "Hello everyone"]
        )

        alice_msgid = alice_echo.tags.get("msgid")
        assert alice_msgid, "Server did not send a msgid tag"

        # Alice can redact her own message (she is also channel operator)
        self.sendLine(alice, f"REDACT {channel} {alice_msgid}")
        alice_redact = self.getMessage(alice)
        bob_redact = self.getMessage(bob)

        # Both should receive the REDACT command
        # No reason provided, so should be exactly 2 params
        self.assertMessageMatch(
            alice_redact,
            command="REDACT",
            params=[channel, alice_msgid],
            prefix=StrRe(f"{alice}!.*"),
        )
        self.assertMessageMatch(
            bob_redact,
            command="REDACT",
            params=[channel, alice_msgid],
            prefix=StrRe(f"{alice}!.*"),
        )

        # Bob sends a message
        self.sendLine(bob, f"PRIVMSG {channel} :Hi Alice")
        bob_echo = self.getMessage(bob)
        alice_delivery = self.getMessage(alice)

        self.assertMessageMatch(
            bob_echo, command="PRIVMSG", params=[channel, "Hi Alice"]
        )
        self.assertMessageMatch(
            alice_delivery, command="PRIVMSG", params=[channel, "Hi Alice"]
        )

        bob_msgid = bob_echo.tags.get("msgid")
        assert bob_msgid, "Server did not send a msgid tag"

        # Alice can redact Bob's message because she is channel operator
        self.sendLine(alice, f"REDACT {channel} {bob_msgid} :spam")
        alice_redact2 = self.getMessage(alice)
        bob_redact2 = self.getMessage(bob)

        self.assertMessageMatch(
            alice_redact2,
            command="REDACT",
            params=[channel, bob_msgid, "spam"],
            prefix=StrRe(f"{alice}!.*"),
        )
        self.assertMessageMatch(
            bob_redact2,
            command="REDACT",
            params=[channel, bob_msgid, "spam"],
            prefix=StrRe(f"{alice}!.*"),
        )

        # Alice sends another message
        self.sendLine(alice, f"PRIVMSG {channel} :Another message")
        alice_echo2 = self.getMessage(alice)
        bob_delivery2 = self.getMessage(bob)

        self.assertMessageMatch(
            alice_echo2, command="PRIVMSG", params=[channel, "Another message"]
        )
        self.assertMessageMatch(
            bob_delivery2, command="PRIVMSG", params=[channel, "Another message"]
        )

        alice_msgid2 = alice_echo2.tags.get("msgid")
        assert alice_msgid2, "Server did not send a msgid tag"

        # Bob cannot redact Alice's message because he is not a channel operator
        self.sendLine(bob, f"REDACT {channel} {alice_msgid2}")
        bob_fail = self.getMessage(bob)

        # Should receive REDACT_FORBIDDEN error
        self.assertMessageMatch(
            bob_fail,
            command="FAIL",
            params=["REDACT", "REDACT_FORBIDDEN", channel, alice_msgid2, ANYSTR],
        )

        # Alice should not receive a REDACT (the redaction was rejected)
        alice_msgs = self.getMessages(alice)
        self.assertEqual(len(alice_msgs), 0)

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactWithReason(self):
        """Test redaction with a reason parameter."""
        alice = random_name("alice")
        channel = random_name("#channel")

        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.joinChannel(alice, channel)
        self.getMessages(alice)

        # Send a message
        self.sendLine(alice, f"PRIVMSG {channel} :Oops wrong channel")
        echo = self.getMessage(alice)
        msgid = echo.tags.get("msgid")
        assert msgid, "Server did not send a msgid tag"

        # Redact with a reason
        self.sendLine(alice, f"REDACT {channel} {msgid} :wrong channel")
        redact = self.getMessage(alice)

        self.assertMessageMatch(
            redact,
            command="REDACT",
            params=[channel, msgid, "wrong channel"],
            prefix=StrRe(f"{alice}!.*"),
        )

    @pytest.mark.arbitrary_client_tags
    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactTagmsg(self):
        """Test redaction of a TAGMSG."""
        alice = random_name("alice")
        bob = random_name("bob")
        channel = random_name("#channel")

        # Connect clients with redaction capability
        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.joinChannel(alice, channel)
        self.getMessages(alice)

        self.connectClient(
            bob,
            name=bob,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
        )
        self.joinChannel(bob, channel)
        self.getMessages(alice)
        self.getMessages(bob)

        # Send a TAGMSG (e.g., a reaction)
        self.sendLine(alice, f"@+draft/react=👍 TAGMSG {channel}")
        echo = self.getMessage(alice)
        delivery = self.getMessage(bob)

        self.assertMessageMatch(echo, command="TAGMSG", params=[channel])
        self.assertMessageMatch(delivery, command="TAGMSG", params=[channel])

        msgid = echo.tags.get("msgid")
        assert msgid, "Server did not send a msgid tag"

        # Redact the TAGMSG
        self.sendLine(alice, f"REDACT {channel} {msgid}")
        alice_redact = self.getMessage(alice)

        # Some servers may not support redacting TAGMSGs (e.g., they don't store them)
        # and return UNKNOWN_MSGID. This is acceptable behavior.
        if alice_redact.command == "FAIL":
            self.assertMessageMatch(
                alice_redact,
                command="FAIL",
                params=["REDACT", "UNKNOWN_MSGID", channel, msgid, ANYSTR],
            )
            # No REDACT was sent, so bob shouldn't receive anything
            bob_msgs = self.getMessages(bob)
            self.assertEqual(len(bob_msgs), 0)
        else:
            # Server supports redacting TAGMSGs
            # No reason provided, so should be exactly 2 params
            bob_redact = self.getMessage(bob)

            self.assertMessageMatch(
                alice_redact,
                command="REDACT",
                params=[channel, msgid],
                prefix=StrRe(f"{alice}!.*"),
            )
            self.assertMessageMatch(
                bob_redact,
                command="REDACT",
                params=[channel, msgid],
                prefix=StrRe(f"{alice}!.*"),
            )

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactNotRelayedToNonSupportingClients(self):
        """Test that REDACT is not sent to clients without the capability."""
        alice = random_name("alice")
        bob = random_name("bob")
        channel = random_name("#channel")

        # Alice has redaction capability
        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.joinChannel(alice, channel)
        self.getMessages(alice)

        # Bob does NOT have redaction capability
        self.connectClient(bob, name=bob, capabilities=["message-tags", "echo-message"])
        self.joinChannel(bob, channel)
        self.getMessages(alice)
        self.getMessages(bob)

        # Alice sends a message
        self.sendLine(alice, f"PRIVMSG {channel} :Test message")
        echo = self.getMessage(alice)
        delivery = self.getMessage(bob)

        self.assertMessageMatch(
            delivery, command="PRIVMSG", params=[channel, "Test message"]
        )

        msgid = echo.tags.get("msgid")
        assert msgid, "Server did not send a msgid tag"

        # Alice redacts the message
        self.sendLine(alice, f"REDACT {channel} {msgid}")
        alice_redact = self.getMessage(alice)

        # Alice should get the REDACT
        # No reason provided, so should be exactly 2 params
        self.assertMessageMatch(
            alice_redact,
            command="REDACT",
            params=[channel, msgid],
            prefix=StrRe(f"{alice}!.*"),
        )

        # Bob should not receive REDACT (or might receive a fallback NOTICE/PRIVMSG)
        # The spec says servers MUST not forward REDACT to non-supporting clients
        bob_msgs = self.getMessages(bob)
        for msg in bob_msgs:
            self.assertNotEqual(
                msg.command,
                "REDACT",
                "REDACT was sent to client without capability",
            )

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactUnknownMsgid(self):
        """Test redacting a message with an unknown msgid."""
        alice = random_name("alice")
        channel = random_name("#channel")

        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.joinChannel(alice, channel)
        self.getMessages(alice)

        # Try to redact a non-existent msgid
        fake_msgid = "nonexistent123"
        self.sendLine(alice, f"REDACT {channel} {fake_msgid}")
        response = self.getMessage(alice)

        # Should receive a FAIL message
        # FAIL REDACT UNKNOWN_MSGID <target> <target-msgid> :message
        if response.command == "FAIL":
            self.assertMessageMatch(
                response,
                command="FAIL",
                params=["REDACT", "UNKNOWN_MSGID", channel, fake_msgid, ANYSTR],
            )

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactInvalidTarget(self):
        """Test redacting with an invalid target."""
        alice = random_name("alice")
        fake_channel = random_name("#fake")

        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.getMessages(alice)

        # Try to redact in a channel alice is not in
        fake_msgid = "somemsgid"
        self.sendLine(alice, f"REDACT {fake_channel} {fake_msgid}")
        response = self.getMessage(alice)

        # Should receive a FAIL message
        # FAIL REDACT INVALID_TARGET <target> :message
        if response.command == "FAIL":
            self.assertMessageMatch(
                response,
                command="FAIL",
                params=["REDACT", "INVALID_TARGET", fake_channel, ANYSTR],
            )

    @pytest.mark.services
    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactDirectMessage(self):
        """Test redacting a direct message between two users."""
        # Enable services for account registration
        self.run_services = True

        alice = random_name("alice")
        bob = random_name("bob")

        # Register and authenticate both users (required for DM redaction on some servers)
        self.controller.registerUser(self, alice, "alice_password")
        self.controller.registerUser(self, bob, "bob_password")

        # Connect both clients with authentication
        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=[
                "sasl",
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.getMessages(alice)

        self.connectClient(
            bob,
            name=bob,
            account=bob,
            password="bob_password",
            capabilities=[
                "sasl",
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
        )
        self.getMessages(bob)

        # Alice sends a direct message to bob
        self.sendLine(alice, f"PRIVMSG {bob} :Private message")
        echo = self.getMessage(alice)
        delivery = self.getMessage(bob)

        self.assertMessageMatch(
            echo, command="PRIVMSG", params=[bob, "Private message"]
        )
        self.assertMessageMatch(
            delivery, command="PRIVMSG", params=[bob, "Private message"]
        )

        msgid = echo.tags.get("msgid")
        assert msgid, "Server did not send a msgid tag"

        # Alice redacts the direct message
        self.sendLine(alice, f"REDACT {bob} {msgid}")
        alice_redact = self.getMessage(alice)
        bob_redact = self.getMessage(bob)

        # Both should receive the REDACT
        # No reason provided, so should be exactly 2 params
        self.assertMessageMatch(
            alice_redact,
            command="REDACT",
            params=[bob, msgid],
            prefix=StrRe(f"{alice}!.*"),
        )
        self.assertMessageMatch(
            bob_redact,
            command="REDACT",
            params=[bob, msgid],
            prefix=StrRe(f"{alice}!.*"),
        )

    @cases.mark_capabilities(
        "message-tags",
        "server-time",
        "echo-message",
        "batch",
        "labeled-response",
        REDACT_CAP,
    )
    def testRedactedMessageDisappearsFromChathistory(self):
        """Test that redacted messages are excluded from CHATHISTORY responses.

        Per the spec, after a message is redacted, CHATHISTORY responses SHOULD either:
        - Exclude it entirely, OR
        - Include a REDACT message after the redacted message
        """
        alice = random_name("alice")
        bob = random_name("bob")
        channel = random_name("#channel")

        # Connect alice
        self.connectClient(
            alice,
            name=alice,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "draft/chathistory",
                REDACT_CAP,
            ],
            skip_if_cap_nak=True,
        )
        self.joinChannel(alice, channel)
        self.getMessages(alice)

        # Connect bob
        self.connectClient(
            bob,
            name=bob,
            capabilities=[
                "message-tags",
                "server-time",
                "echo-message",
                "batch",
                "labeled-response",
                "draft/chathistory",
                REDACT_CAP,
            ],
        )
        self.joinChannel(bob, channel)
        self.getMessages(alice)
        self.getMessages(bob)

        # Alice sends a message
        self.sendLine(alice, f"PRIVMSG {channel} :This message will be redacted")
        echo = self.getMessage(alice)
        delivery = self.getMessage(bob)

        self.assertMessageMatch(
            echo, command="PRIVMSG", params=[channel, "This message will be redacted"]
        )
        self.assertMessageMatch(
            delivery,
            command="PRIVMSG",
            params=[channel, "This message will be redacted"],
        )

        msgid = echo.tags.get("msgid")
        assert msgid, "Server did not send a msgid tag"

        # Bob retrieves chat history and should see the message
        self.sendLine(bob, f"CHATHISTORY LATEST {channel} * 10")
        messages = self.getMessages(bob)

        # Extract PRIVMSG messages from the batch
        privmsgs_before = [
            msg
            for msg in messages
            if msg.command == "PRIVMSG" and channel in msg.params
        ]
        self.assertGreater(
            len(privmsgs_before),
            0,
            "Bob should see at least one message in CHATHISTORY before redaction",
        )

        # Verify the exact message is present with correct msgid and text
        found_message = False
        for msg in privmsgs_before:
            if (
                msg.tags.get("msgid") == msgid
                and msg.params[-1] == "This message will be redacted"
            ):
                found_message = True
                break
        self.assertTrue(
            found_message,
            f"Original message with msgid {msgid} and exact text should be in CHATHISTORY before redaction",
        )

        # Alice redacts the message
        self.sendLine(alice, f"REDACT {channel} {msgid}")
        self.getMessage(alice)  # Alice's REDACT echo
        self.getMessage(bob)  # Bob's REDACT delivery

        # Bob retrieves chat history again
        self.sendLine(bob, f"CHATHISTORY LATEST {channel} * 10")
        messages_after = self.getMessages(bob)

        # Extract PRIVMSG and REDACT messages from the batch
        privmsgs_after = [
            msg
            for msg in messages_after
            if msg.command == "PRIVMSG" and channel in msg.params
        ]
        redacts_after = [
            msg
            for msg in messages_after
            if msg.command == "REDACT" and channel in msg.params
        ]

        # Per spec: the message should either be excluded entirely,
        # or a REDACT should be included after it
        found_original_after_redaction = False

        for msg in privmsgs_after:
            if (
                msg.tags.get("msgid") == msgid
                or "This message will be redacted" in msg.params[-1]
            ):
                found_original_after_redaction = True
                break

        # If the original message is still present, there should be a REDACT for it
        if found_original_after_redaction:
            # Find a REDACT that matches our message
            # REDACT format: REDACT <target> <msgid> [<reason>]
            matching_redact = None
            for redact_msg in redacts_after:
                if (
                    len(redact_msg.params) >= 2
                    and redact_msg.params[0] == channel
                    and redact_msg.params[1] == msgid
                ):
                    matching_redact = redact_msg
                    break

            self.assertIsNotNone(
                matching_redact,
                f"If redacted message is in CHATHISTORY, a REDACT with target={channel} and msgid={msgid} should also be present",
            )
        # Otherwise, the message was excluded entirely (preferred behavior)
        else:
            # Message was excluded - this is acceptable
            pass
