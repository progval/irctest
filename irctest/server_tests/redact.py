"""
`IRCv3 draft message-redaction
<https://ircv3.net/specs/extensions/message-redaction>`_
"""

from irctest import cases, runner
from irctest.irc_utils.junkdrawer import random_name
from irctest.patma import ANYDICT, ANYSTR, Either, StrRe
from irctest.specifications import Capabilities

REDACT_CAP = Capabilities.MESSAGE_REDACTION.value


class RedactTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(chathistory=True)

    def _setupTwoClientsAndChannel(self):
        """Connect two clients (alice and bob) with redaction capability and join a channel.

        Returns:
            tuple: (alice_nick, bob_nick, channel_name)
        """
        alice = random_name("alys")  # work around Sable nick limit
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

        return alice, bob, channel

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testOpRedactSelfPrivmsg(self):
        """Tests that a channel operator can redact a message they sent themselves."""
        alice, bob, channel = self._setupTwoClientsAndChannel()

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

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testOpRedactOthersPrivmsg(self):
        """Tests that a channel operator can redact another user's message."""
        alice, bob, channel = self._setupTwoClientsAndChannel()

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
        alice_redact = self.getMessage(alice)
        bob_redact = self.getMessage(bob)

        self.assertMessageMatch(
            alice_redact,
            command="REDACT",
            params=[channel, bob_msgid, "spam"],
            prefix=StrRe(f"{alice}!.*"),
        )
        self.assertMessageMatch(
            bob_redact,
            command="REDACT",
            params=[channel, bob_msgid, "spam"],
            prefix=StrRe(f"{alice}!.*"),
        )

    @cases.mark_specifications("Ergo")
    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testOperCanRedactInUnjoinedChannel(self):
        """Tests that an IRC operator can redact a message in a channel they
        are not joined to."""
        alice, bob, channel = self._setupTwoClientsAndChannel()

        ircop = random_name("ircop")
        self.connectClient(
            ircop,
            name=ircop,
            capabilities=[
                "message-tags",
                "echo-message",
                "batch",
                "labeled-response",
                REDACT_CAP,
            ],
        )
        self.getMessages(ircop)

        self.sendLine(ircop, "OPER operuser operpassword")
        self.getMessages(ircop)

        # Bob sends a message in the channel
        self.sendLine(bob, f"PRIVMSG {channel} :Hi Alice")
        bob_echo = self.getMessage(bob)
        alice_delivery = self.getMessage(alice)

        bob_msgid = bob_echo.tags.get("msgid")
        assert bob_msgid, "Server did not send a msgid tag"

        for msg in (bob_echo, alice_delivery):
            self.assertMessageMatch(
                msg,
                command="PRIVMSG",
                params=[channel, "Hi Alice"],
                tags={"msgid": bob_msgid, **ANYDICT},
            )

        # The IRC operator, who is not joined to the channel, can still
        # redact Bob's message. The REDACT is relayed to the channel's
        # members (alice and bob), as well as to the operator themselves,
        # even though they are not a member of the channel.
        self.sendLine(ircop, f"REDACT {channel} {bob_msgid} :spam")

        ircop_redact = self.getMessage(ircop)
        alice_redact = self.getMessage(alice)
        bob_redact = self.getMessage(bob)

        for msg in (ircop_redact, alice_redact, bob_redact):
            self.assertMessageMatch(
                msg,
                command="REDACT",
                params=[channel, bob_msgid, "spam"],
                prefix=StrRe(f"{ircop}!.*"),
            )

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testCantRedactOthersPrivmsg(self):
        """Tests that a non-operator cannot redact another user's message."""
        alice, bob, channel = self._setupTwoClientsAndChannel()

        # Alice sends a message
        self.sendLine(alice, f"PRIVMSG {channel} :Another message")
        alice_echo = self.getMessage(alice)
        bob_delivery = self.getMessage(bob)

        self.assertMessageMatch(
            alice_echo, command="PRIVMSG", params=[channel, "Another message"]
        )
        self.assertMessageMatch(
            bob_delivery, command="PRIVMSG", params=[channel, "Another message"]
        )

        alice_msgid = alice_echo.tags.get("msgid")
        assert alice_msgid, "Server did not send a msgid tag"

        # Bob cannot redact Alice's message because he is not a channel operator
        self.sendLine(bob, f"REDACT {channel} {alice_msgid}")
        bob_fail = self.getMessage(bob)

        # Should receive REDACT_FORBIDDEN error
        self.assertMessageMatch(
            bob_fail,
            command="FAIL",
            params=["REDACT", "REDACT_FORBIDDEN", channel, alice_msgid, ANYSTR],
        )

        # Alice should not receive a REDACT (the redaction was rejected)
        alice_msgs = self.getMessages(alice)
        self.assertEqual(len(alice_msgs), 0)

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactWithReason(self):
        """Test redaction with a reason parameter."""
        alice = random_name("alys")
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

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactTagmsg(self):
        """Test redaction of a TAGMSG."""
        alice, bob, channel = self._setupTwoClientsAndChannel()

        clienttagdeny = self.server_support.get("CLIENTTAGDENY")
        if clienttagdeny:
            parts = clienttagdeny.split(",")
            if "*" in parts and "+draft/reply" not in parts:
                raise runner.ImplementationChoice("CLIENTTAGDENY blocks +draft/reply")

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
            self.assertEqual(bob_msgs, [])
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
        alice = random_name("alys")
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
        alice = random_name("alys")
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
        alice = random_name("alys")
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

        self.assertMessageMatch(
            response,
            command="FAIL",
            params=["REDACT", "INVALID_TARGET", fake_channel, ANYSTR],
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
        alice = random_name("alys")
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
        # request event-playback cap so that Ergo doesn't send HistServ messages,
        # but don't skip the test if it's not available
        self.sendLine(alice, "CAP REQ draft/event-playback")
        self.sendLine(bob, "CAP REQ draft/event-playback")
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
        batch_id, batch_params, messages = self.getBatchMessages(bob, "chathistory")

        # CHATHISTORY should return exactly one PRIVMSG
        (privmsg_before,) = [msg for msg in messages if msg.command == "PRIVMSG"]

        # Verify the exact message is present with correct msgid and text
        self.assertMessageMatch(
            privmsg_before,
            command="PRIVMSG",
            params=[channel, "This message will be redacted"],
        )
        self.assertEqual(privmsg_before.tags.get("msgid"), msgid)

        # Alice redacts the message
        self.sendLine(alice, f"REDACT {channel} {msgid}")
        self.getMessage(alice)  # Alice's REDACT echo
        self.getMessage(bob)  # Bob's REDACT delivery

        # Bob retrieves chat history again
        self.sendLine(bob, f"CHATHISTORY LATEST {channel} * 10")
        batch_id_after, batch_params_after, messages_after = self.getBatchMessages(
            bob, "chathistory"
        )

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


@cases.mark_services
class RedactWithServicesTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(chathistory=True)

    @cases.mark_capabilities(
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testRedactDirectMessage(self):
        """Test redacting a direct message between two users."""
        alice = random_name("alys")
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
        "message-tags", "echo-message", "batch", "labeled-response", REDACT_CAP
    )
    def testOpInOtherChannelCanRedactOwnButNotOthers(self):
        """Tests that being a channel operator in one channel does not grant
        redaction privileges in another channel: alice can still redact her
        own messages in #bob, but cannot redact bob's messages there."""
        alice = random_name("alys")
        bob = random_name("bob")
        alice_channel = random_name("#alice")
        bob_channel = random_name("#bob")

        # Redacting one's own messages requires an authenticated account
        self.controller.registerUser(self, alice, "alice_password")

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
        # Alice joins her own channel first and becomes channel operator there
        self.joinChannel(alice, alice_channel)
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
        # Bob joins his own channel first and becomes channel operator there
        self.joinChannel(bob, bob_channel)
        self.getMessages(bob)

        # Alice joins bob's channel afterward, so she is not an operator there
        self.joinChannel(alice, bob_channel)
        self.getMessages(alice)
        self.getMessages(bob)

        # Alice sends a message in bob's channel and can redact her own message,
        # even though she is not a channel operator there
        self.sendLine(alice, f"PRIVMSG {bob_channel} :Hello from alice")
        alice_echo = self.getMessage(alice)
        bob_delivery = self.getMessage(bob)

        self.assertMessageMatch(
            alice_echo,
            command="PRIVMSG",
            params=[bob_channel, "Hello from alice"],
            tags={"msgid": ANYSTR, **ANYDICT},
        )
        alice_msgid = alice_echo.tags["msgid"]
        self.assertMessageMatch(
            bob_delivery,
            command="PRIVMSG",
            params=[bob_channel, "Hello from alice"],
            tags={"msgid": alice_msgid, **ANYDICT},
        )

        self.sendLine(alice, f"REDACT {bob_channel} {alice_msgid}")
        alice_redact = self.getMessage(alice)
        bob_redact = self.getMessage(bob)

        for msg in (alice_redact, bob_redact):
            self.assertMessageMatch(
                msg,
                command="REDACT",
                params=[bob_channel, alice_msgid],
                prefix=StrRe(f"{alice}!.*"),
            )

        # Bob sends a message in his own channel
        self.sendLine(bob, f"PRIVMSG {bob_channel} :Hello from bob")
        bob_echo = self.getMessage(bob)
        alice_delivery = self.getMessage(alice)

        self.assertMessageMatch(
            bob_echo, command="PRIVMSG", params=[bob_channel, "Hello from bob"]
        )
        self.assertMessageMatch(
            alice_delivery, command="PRIVMSG", params=[bob_channel, "Hello from bob"]
        )

        bob_msgid = bob_echo.tags.get("msgid")
        assert bob_msgid, "Server did not send a msgid tag"

        # Alice cannot redact bob's message: she is a channel operator in
        # #alice, but not in #bob
        self.sendLine(alice, f"REDACT {bob_channel} {bob_msgid}")
        alice_fail = self.getMessage(alice)

        self.assertMessageMatch(
            alice_fail,
            command="FAIL",
            params=["REDACT", "REDACT_FORBIDDEN", bob_channel, bob_msgid, ANYSTR],
        )

        # Bob should not receive a REDACT (the redaction was rejected)
        bob_msgs = self.getMessages(bob)
        self.assertEqual(bob_msgs, [])

        # Alice cannot redact bob's message by claiming it belongs to
        # #alice, the channel where she *is* a channel operator: her
        # operator status there does not carry over to bob's message
        self.sendLine(alice, f"REDACT {alice_channel} {bob_msgid}")
        alice_fail_wrong_channel = self.getMessage(alice)

        self.assertMessageMatch(
            alice_fail_wrong_channel,
            command="FAIL",
            params=[
                "REDACT",
                Either("REDACT_FORBIDDEN", "UNKNOWN_MSGID"),
                alice_channel,
                bob_msgid,
                ANYSTR,
            ],
        )

        # Bob should not receive a REDACT (the redaction was rejected)
        bob_msgs = self.getMessages(bob)
        self.assertEqual(bob_msgs, [])
