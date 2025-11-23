"""
Tests for the OPER command.

The OPER command is used to obtain IRC operator privileges.
See `RFC 1459 <https://datatracker.ietf.org/doc/html/rfc1459#section-4.1.5>`__
and `RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.1.4>`__.
and <https://modern.ircdocs.horse/#oper-message>
"""

from irctest import cases
from irctest.numerics import (
    ERR_NEEDMOREPARAMS,
    ERR_NOOPERHOST,
    ERR_PASSWDMISMATCH,
    RPL_YOUREOPER,
)
from irctest.patma import ANYSTR


class OperTestCase(cases.BaseServerTestCase):
    def _assertNumericPresent(self, messages, numerics, expected_nick):
        """Helper to check that a numeric has correct two-parameter syntax.

        Args:
            messages: List of messages to search
            numeric: The numeric command to check
            expected_nick: Expected nickname in first parameter
        """
        numeric_messages = [msg for msg in messages if msg.command in numerics]
        self.assertTrue(
            len(numeric_messages) > 0,
            msg=f"Expected at least one {numerics} message",
        )
        for msg in numeric_messages:
            if msg.command == ERR_NEEDMOREPARAMS:
                # some ircds echo the command back as the second parameter
                self.assertEqual(msg.params[0], expected_nick)
            else:
                # normal numeric format: nick and freeform trailing
                self.assertMessageMatch(msg, params=[expected_nick, ANYSTR])

    @cases.mark_specifications("Modern")
    def testOperSuccess(self):
        """Test successful OPER authentication."""
        self.connectClient("baz", name="baz")
        self.sendLine("baz", "OPER operuser operpassword")
        messages = self.getMessages("baz")

        self._assertNumericPresent(messages, [RPL_YOUREOPER], "baz")

        # Check that the user receives +o mode
        mode_messages = [msg for msg in messages if msg.command == "MODE"]
        self.assertEqual(
            len(mode_messages),
            1,
            msg="Expected MODE message after successful OPER command",
        )
        mode_message = mode_messages[0]
        # additional parameters are possible, e.g. if the user received a snomask
        self.assertGreaterEqual(len(mode_message.params), 2)
        self.assertEqual(mode_message.params[0], "baz")
        self.assertTrue(mode_message.params[1].startswith("+"))
        self.assertIn("o", mode_message.params[1])

    @cases.mark_specifications("Modern")
    def testOperFailure(self):
        """Test failed OPER authentication with incorrect password."""
        self.connectClient("baz", name="baz")
        self.sendLine("baz", "OPER operuser nottheoperpassword")
        messages = self.getMessages("baz")

        commands = {msg.command for msg in messages}
        self._assertNumericPresent(
            messages, [ERR_NOOPERHOST, ERR_PASSWDMISMATCH], "baz"
        )

        # Ensure RPL_YOUREOPER was NOT sent
        self.assertNotIn(
            RPL_YOUREOPER,
            commands,
            msg="RPL_YOUREOPER (381) should not be sent for failed OPER attempt",
        )

    @cases.mark_specifications("Modern")
    def testOperNoPassword(self):
        """Test OPER command with no password argument."""
        self.connectClient("baz", name="baz")
        self.sendLine("baz", "OPER operuser")
        messages = self.getMessages("baz")

        commands = {msg.command for msg in messages}
        self._assertNumericPresent(
            messages, [ERR_NOOPERHOST, ERR_PASSWDMISMATCH, ERR_NEEDMOREPARAMS], "baz"
        )

        # Ensure RPL_YOUREOPER was NOT sent
        self.assertNotIn(
            RPL_YOUREOPER,
            commands,
            msg="RPL_YOUREOPER (381) should not be sent for OPER with no password",
        )

    @cases.mark_specifications("Modern")
    def testOperNonexistentUser(self):
        """Test OPER command with nonexistent oper username."""
        self.connectClient("baz", name="baz")
        self.sendLine("baz", "OPER notanoperuser somepassword")
        messages = self.getMessages("baz")

        commands = {msg.command for msg in messages}
        self._assertNumericPresent(
            messages, [ERR_NOOPERHOST, ERR_PASSWDMISMATCH], "baz"
        )

        # Ensure RPL_YOUREOPER was NOT sent
        self.assertNotIn(
            RPL_YOUREOPER,
            commands,
            msg="RPL_YOUREOPER (381) should not be sent for OPER with nonexistent username",
        )
