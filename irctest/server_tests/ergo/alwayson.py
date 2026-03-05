"""
`Ergo <https://ergo.chat/>`-specific tests of always-on functionality.
"""

from irctest import cases
from irctest.controllers.ergo import BASE_CAPS
from irctest.irc_utils.junkdrawer import parse_rplnamreply
from irctest.numerics import RPL_TOPIC


@cases.mark_services
class AlwaysOnTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def test_always_on_persistence_after_disconnect(self):
        """Test that enabling always-on keeps user present after disconnect."""
        alice = "alice"
        bob = "bob"

        # Register and connect alice
        self.controller.registerUser(self, alice, "alice_password")
        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )

        # Enable always-on for alice
        self.sendLine(alice, "PRIVMSG NickServ :set always-on true")
        self.getMessages(alice)

        # Join a channel
        self.joinChannel(alice, "#test")
        self.getMessages(alice)

        # Connect bob to observe alice's presence
        self.connectClient(bob, name=bob, capabilities=BASE_CAPS)
        self.sendLine(bob, "JOIN #test")
        msgs = self.getMessages(bob)

        # Verify both alice and bob are in the channel
        # alice should have @ since she created the channel
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"@alice", "bob"})

        # Disconnect alice's client
        self.sendLine(alice, "QUIT")
        self.assertDisconnected(alice)

        # Bob should still see alice in the channel (always-on keeps her present)
        # and alice should still have operator status
        self.sendLine(bob, "NAMES #test")
        msgs = self.getMessages(bob)
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"@alice", "bob"})

        # Reconnect alice and verify she's automatically back in the channel
        msgs = self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )
        self.assertTrue(
            any(
                self.messageEqual(msg, command="JOIN", params=["#test"]) for msg in msgs
            ),
            "Did not receive expected JOIN line on reconnection",
        )

        # Alice should automatically be in her channels with operator status preserved
        # Send a NAMES request to verify she's in the channel
        self.sendLine(alice, "NAMES #test")
        msgs = self.getMessages(alice)
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"@alice", "bob"})

    @cases.mark_specifications("Ergo")
    def test_always_on_persistence_after_restart(self):
        """Test that always-on users remain present after server restart."""
        alice = "alice"
        bob = "bob"

        # Register and connect alice
        self.controller.registerUser(self, alice, "alice_password")
        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )

        # Enable always-on for alice
        self.sendLine(alice, "PRIVMSG NickServ :set always-on true")
        self.getMessages(alice)

        # Join a channel
        self.joinChannel(alice, "#test")
        self.getMessages(alice)

        # Restart the server
        self.controller.restart()

        # Connect bob to check if alice is still present
        self.connectClient(bob, name=bob, capabilities=BASE_CAPS)
        self.sendLine(bob, "JOIN #test")
        msgs = self.getMessages(bob)

        # Alice should still be in the channel after restart with @ status preserved
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"@alice", "bob"})

        # reconnect Alice and assert that she gets a JOIN line for her channel
        msgs = self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )
        self.assertTrue(
            any(
                self.messageEqual(msg, command="JOIN", params=["#test"]) for msg in msgs
            ),
            "Did not receive expected JOIN line on reconnection",
        )

    @cases.mark_specifications("Ergo")
    def test_always_on_with_channel_registration(self):
        """Test always-on with channel registration persistence."""
        alice = "alice"
        bob = "bob"

        # Register and connect alice
        self.controller.registerUser(self, alice, "alice_password")
        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )

        # Enable always-on for alice
        self.sendLine(alice, "PRIVMSG NickServ :set always-on true")
        self.getMessages(alice)

        # Join and register a channel
        self.joinChannel(alice, "#alice")
        self.sendLine(alice, "TOPIC #alice :alice's always-on channel")
        self.getMessages(alice)

        self.sendLine(alice, "PRIVMSG ChanServ :register #alice")
        msgs = self.getMessages(alice)
        success = any(
            self.messageEqual(msg, command="MODE", params=["#alice", "+q", "alice"])
            for msg in msgs
        )
        self.assertTrue(
            success,
            f"Did not receive successful MODE +q for registration: {msgs}",
        )

        # Restart the server
        self.controller.restart()

        # Connect bob - alice should still be in her channel
        self.connectClient(bob, name=bob, capabilities=BASE_CAPS)
        self.sendLine(bob, "JOIN #alice")
        msgs = self.getMessages(bob)

        # Alice should be present due to always-on with founder status (~) preserved
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"~alice", "bob"})

        # Verify topic persistence (RPL_TOPIC is sent as numeric 332)
        topic_msgs = [msg for msg in msgs if msg.command == RPL_TOPIC]
        self.assertTrue(
            len(topic_msgs) > 0,
            "Topic should be present after restart",
        )

    @cases.mark_specifications("Ergo")
    def test_always_on_can_be_disabled(self):
        """Test that users can disable always-on after enabling it."""
        alice = "alice"
        bob = "bob"

        # Register and connect alice
        self.controller.registerUser(self, alice, "alice_password")
        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )

        # Enable always-on for alice
        self.sendLine(alice, "PRIVMSG NickServ :set always-on true")
        self.getMessages(alice)

        # Join a channel
        self.joinChannel(alice, "#test")
        self.getMessages(alice)

        # Connect bob to observe
        self.connectClient(bob, name=bob, capabilities=BASE_CAPS)
        self.sendLine(bob, "JOIN #test")
        msgs = self.getMessages(bob)

        # Both should be in the channel
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"@alice", "bob"})

        # Disconnect alice's client
        self.sendLine(alice, "QUIT")
        self.assertDisconnected(alice)

        # Bob should NOT see a QUIT message (always-on keeps alice present)
        msgs = self.getMessages(bob)
        quit_msgs = [msg for msg in msgs if msg.command == "QUIT"]
        self.assertEqual(
            len(quit_msgs), 0, "Bob should not see alice's QUIT with always-on"
        )

        # Alice should still be present (always-on is enabled)
        self.sendLine(bob, "NAMES #test")
        msgs = self.getMessages(bob)
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"@alice", "bob"})

        # Reconnect alice and disable always-on
        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )
        self.sendLine(alice, "PRIVMSG NickServ :set always-on false")
        self.getMessages(alice)

        # Disconnect alice again
        self.sendLine(alice, "QUIT")
        self.assertDisconnected(alice)

        # Bob should see alice's QUIT message (always-on is disabled)
        msgs = self.getMessages(bob)
        quit_msgs = [msg for msg in msgs if msg.command == "QUIT"]
        self.assertEqual(len(quit_msgs), 1, "Bob should see alice's QUIT")
        self.assertTrue(
            quit_msgs[0].prefix.startswith("alice!"),
            f"QUIT should be from alice, got: {quit_msgs[0].prefix}",
        )

        # Verify alice is no longer in the channel
        self.sendLine(bob, "NAMES #test")
        msgs = self.getMessages(bob)
        names = parse_rplnamreply(msgs)
        self.assertEqual(names, {"bob"})
