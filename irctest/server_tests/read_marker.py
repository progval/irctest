"""
`Draft IRCv3 read-marker <https://ircv3.net/specs/extensions/read-marker>`_
"""

from irctest import cases
from irctest.irc_utils.junkdrawer import random_name

CAP_NAME = "draft/read-marker"


class _BaseReadMarkerTestCase(cases.BaseServerTestCase):
    def getMarkread(self, client):
        """Return the single MARKREAD from the next group of messages, or fail."""
        msgs = self.getMessages(client)
        markread = [m for m in msgs if m.command == "MARKREAD"]
        self.assertEqual(len(markread), 1, markread)
        return markread[0]


class ReadMarkerTestCase(_BaseReadMarkerTestCase):
    @cases.mark_capabilities("draft/read-marker")
    def testGetNoReadMarker(self):
        """MARKREAD get on a target with no stored timestamp returns '*'."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.getMessages(1)

        self.sendLine(1, "MARKREAD #nosuchtarget")
        self.assertMessageMatch(
            self.getMarkread(1), command="MARKREAD", params=["#nosuchtarget", "*"]
        )

    @cases.mark_capabilities("draft/read-marker")
    def testSetAndGet(self):
        """MARKREAD get after a set returns the stored timestamp."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.joinChannel(1, "#test")
        self.getMessages(1)

        ts = "2019-01-04T14:33:26.123Z"
        self.sendLine(1, f"MARKREAD #test timestamp={ts}")
        self.getMessages(1)

        self.sendLine(1, "MARKREAD #test")
        self.assertMessageMatch(
            self.getMarkread(1), command="MARKREAD", params=["#test", f"timestamp={ts}"]
        )

    @cases.mark_capabilities("draft/read-marker")
    def testReadMarkerDoesNotDecrease(self):
        """If a client sends a MARKREAD with an older timestamp, the server MUST
        reply with the newer stored value (spec: 'The last read timestamp of a
        target MUST only ever increase')."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.joinChannel(1, "#test")
        self.getMessages(1)

        newer_ts = "2019-06-01T12:00:00.000Z"
        older_ts = "2019-01-01T00:00:00.000Z"

        self.sendLine(1, f"MARKREAD #test timestamp={newer_ts}")
        self.getMessages(1)

        # Try to set an older timestamp; server MUST reply with the newer stored value
        self.sendLine(1, f"MARKREAD #test timestamp={older_ts}")
        self.assertMessageMatch(
            self.getMarkread(1),
            command="MARKREAD",
            params=["#test", f"timestamp={newer_ts}"],
        )

    @cases.mark_capabilities("draft/read-marker")
    def testReadMarkerOnJoin(self):
        """After JOIN, server MUST send MARKREAD before RPL_ENDOFNAMES (366)."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.sendLine(1, "JOIN #test")
        msgs = self.getMessages(1)

        # Find the position of MARKREAD and 366 (RPL_ENDOFNAMES)
        commands = [m.command for m in msgs]
        self.assertIn(
            "MARKREAD",
            commands,
            "Expected MARKREAD after JOIN when draft/read-marker is negotiated",
        )
        self.assertIn("366", commands, "Expected RPL_ENDOFNAMES after JOIN")
        markread_idx = commands.index("MARKREAD")
        endofnames_idx = commands.index("366")
        self.assertLess(
            markread_idx,
            endofnames_idx,
            "MARKREAD MUST be sent before RPL_ENDOFNAMES (366)",
        )
        # Channel with no prior read marker → timestamp is '*'
        self.assertMessageMatch(
            msgs[markread_idx], command="MARKREAD", params=["#test", "*"]
        )

    @cases.mark_capabilities("draft/read-marker")
    def testReadMarkerOnJoinWithStoredTimestamp(self):
        """After JOIN, MARKREAD sent by server reflects any previously stored timestamp."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.joinChannel(1, "#test")
        self.getMessages(1)

        ts = "2020-03-15T10:00:00.000Z"
        self.sendLine(1, f"MARKREAD #test timestamp={ts}")
        self.getMessages(1)

        # Part and rejoin
        self.sendLine(1, "PART #test")
        self.getMessages(1)
        self.sendLine(1, "JOIN #test")
        msgs = self.getMessages(1)

        commands = [m.command for m in msgs]
        self.assertIn("MARKREAD", commands)
        markread_idx = commands.index("MARKREAD")
        self.assertMessageMatch(
            msgs[markread_idx],
            command="MARKREAD",
            params=["#test", f"timestamp={ts}"],
        )

    @cases.mark_capabilities("draft/read-marker")
    def testReadMarkerUserTarget(self):
        """MARKREAD get for a user (DM) target returns the stored value."""
        nick = random_name("alice")
        bob = random_name("bob")

        self.connectClient(nick, capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.connectClient(bob, name=2)
        self.getMessages(1)
        self.getMessages(2)

        ts = "2023-07-04T00:00:00.000Z"
        self.sendLine(1, f"MARKREAD {bob} timestamp={ts}")
        self.assertMessageMatch(
            self.getMarkread(1), command="MARKREAD", params=[bob, f"timestamp={ts}"]
        )

        # Now get it back explicitly
        self.sendLine(1, f"MARKREAD {bob}")
        self.assertMessageMatch(
            self.getMarkread(1), command="MARKREAD", params=[bob, f"timestamp={ts}"]
        )

    @cases.mark_capabilities("draft/read-marker")
    def testMissingParams(self):
        """MARKREAD with no parameters → FAIL MARKREAD NEED_MORE_PARAMS."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.getMessages(1)

        self.sendLine(1, "MARKREAD")
        msgs = self.getMessages(1)
        fail_msgs = [m for m in msgs if m.command == "FAIL"]
        self.assertTrue(
            any(m.params[:2] == ["MARKREAD", "NEED_MORE_PARAMS"] for m in fail_msgs),
            f"Expected FAIL MARKREAD NEED_MORE_PARAMS, got: {fail_msgs}",
        )

    @cases.mark_capabilities("draft/read-marker")
    def testInvalidTimestamp(self):
        """MARKREAD set with a malformed timestamp → FAIL MARKREAD INVALID_PARAMS."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.joinChannel(1, "#test")
        self.getMessages(1)

        self.sendLine(1, "MARKREAD #test timestamp=not-a-timestamp")
        msgs = self.getMessages(1)
        fail_msgs = [m for m in msgs if m.command == "FAIL"]
        self.assertTrue(
            any(m.params[:2] == ["MARKREAD", "INVALID_PARAMS"] for m in fail_msgs),
            f"Expected FAIL MARKREAD INVALID_PARAMS, got: {fail_msgs}",
        )

    @cases.mark_capabilities("draft/read-marker")
    def testWildcardTimestampRejected(self):
        """MARKREAD client set command MUST NOT use '*' as the timestamp."""
        self.connectClient("alice", capabilities=[CAP_NAME], skip_if_cap_nak=True)
        self.joinChannel(1, "#test")
        self.getMessages(1)

        # '*' is a valid timestamp= parameter only in server→client direction;
        # as a client set command it must be rejected.
        self.sendLine(1, "MARKREAD #test *")
        msgs = self.getMessages(1)
        fail_msgs = [m for m in msgs if m.command == "FAIL"]
        self.assertTrue(
            any(m.params[:2] == ["MARKREAD", "INVALID_PARAMS"] for m in fail_msgs),
            f"Expected FAIL MARKREAD INVALID_PARAMS for '*' timestamp, got: {msgs}",
        )


@cases.mark_services
class ReadMarkerServiceTestCase(_BaseReadMarkerTestCase):
    """Tests requiring account registration."""

    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        """Make always-on the default so that read markers persist across reconnects
        (in Ergo, persistence requires always-on to be enabled).
        """
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"]["multiclient"].update(
                {"always-on": "opt-out"}
            )
        )

    @cases.mark_capabilities("draft/read-marker")
    def testReadMarkerPersistsAcrossReconnect(self):
        """Read marker set in one session persists when reconnecting."""
        nick = random_name("alice")
        pw = random_name("pw")
        self.controller.registerUser(self, nick, pw)

        self.connectClient(
            nick,
            capabilities=[CAP_NAME, "sasl"],
            password=pw,
            skip_if_cap_nak=True,
        )
        self.joinChannel(1, "#test")
        self.getMessages(1)

        ts = "2021-05-20T08:30:00.000Z"
        self.sendLine(1, f"MARKREAD #test timestamp={ts}")
        self.getMessages(1)

        # Disconnect and reconnect. A persistent client should be re-joined
        # to its channels, receiving JOIN and MARKREAD at the end of the connection
        # burst.
        self.removeClient(1)

        msgs = self.connectClient(
            nick,
            name=2,
            capabilities=[CAP_NAME, "sasl"],
            password=pw,
        )
        # Drain any remaining messages after the welcome burst
        msgs.extend(self.getMessages(2))

        markread_msgs = [m for m in msgs if m.command == "MARKREAD"]
        self.assertTrue(
            len(markread_msgs) >= 1,
            "Expected MARKREAD on reconnect after always-on rejoin",
        )
        # Find the MARKREAD for #test specifically
        channel_markread = [m for m in markread_msgs if m.params[0] == "#test"]
        self.assertEqual(len(channel_markread), 1, channel_markread)
        self.assertMessageMatch(
            channel_markread[0],
            command="MARKREAD",
            params=["#test", f"timestamp={ts}"],
        )

    @cases.mark_capabilities("draft/read-marker")
    def testReadMarkerPropagatedToOtherSessions(self):
        """When a user sets a read marker, the server SHOULD send MARKREAD to
        all other sessions of the same user that have the capability negotiated."""
        nick = random_name("alice")
        pw = random_name("pw")
        self.controller.registerUser(self, nick, pw)

        # Connect first session
        self.connectClient(
            nick,
            name="s1",
            capabilities=[CAP_NAME, "sasl"],
            password=pw,
            skip_if_cap_nak=True,
        )
        self.joinChannel("s1", "#test")
        self.getMessages("s1")

        # Connect second session for the same account
        self.connectClient(
            nick, name="s2", capabilities=[CAP_NAME, "sasl"], password=pw
        )
        self.getMessages("s2")

        # s1 sets a read marker
        ts = "2022-11-11T11:11:11.111Z"
        self.sendLine("s1", f"MARKREAD #test timestamp={ts}")
        self.getMessages("s1")

        # s2 should receive a MARKREAD for the same target
        self.assertMessageMatch(
            self.getMarkread("s2"),
            command="MARKREAD",
            params=["#test", f"timestamp={ts}"],
        )
