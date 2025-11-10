"""
Tests for the OPER command.

The OPER command is used to obtain IRC operator privileges.
See `RFC 1459 <https://datatracker.ietf.org/doc/html/rfc1459#section-4.1.5>`__
and `RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.1.4>`__.
"""

from irctest import cases
from irctest.numerics import ERR_NOOPERHOST, RPL_YOUREOPER


class OperTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testOperSuccess(self):
        """Test successful OPER authentication."""
        self.connectClient("oper_user", name="oper_user")
        self.sendLine("oper_user", "OPER operuser operpassword")
        messages = self.getMessages("oper_user")

        commands = {msg.command for msg in messages}
        self.assertIn(
            RPL_YOUREOPER,
            commands,
            msg="Expected RPL_YOUREOPER (381) in response to successful OPER command",
        )

        # Check that the user receives +o mode
        mode_messages = [msg for msg in messages if msg.command == "MODE"]
        self.assertTrue(
            len(mode_messages) > 0,
            msg="Expected MODE message after successful OPER command",
        )

        # Verify that at least one MODE message contains +o
        has_oper_mode = any("+o" in " ".join(msg.params) for msg in mode_messages)
        self.assertTrue(
            has_oper_mode,
            msg="Expected MODE message to contain +o after successful OPER command",
        )

    @cases.mark_specifications("Ergo")
    def testOperFailure(self):
        """Test failed OPER authentication with incorrect password."""
        self.connectClient("oper_user", name="oper_user")
        self.sendLine("oper_user", "OPER operuser nottheoperpassword")
        messages = self.getMessages("oper_user")

        commands = {msg.command for msg in messages}
        self.assertIn(
            ERR_NOOPERHOST,
            commands,
            msg="Expected ERR_NOOPERHOST (491) in response to OPER with incorrect password",
        )

        # Ensure RPL_YOUREOPER was NOT sent
        self.assertNotIn(
            RPL_YOUREOPER,
            commands,
            msg="RPL_YOUREOPER (381) should not be sent for failed OPER attempt",
        )

    @cases.mark_specifications("Ergo")
    def testOperNoPassword(self):
        """Test OPER command with no password argument."""
        self.connectClient("oper_user", name="oper_user")
        self.sendLine("oper_user", "OPER operuser")
        messages = self.getMessages("oper_user")

        commands = {msg.command for msg in messages}
        self.assertIn(
            ERR_NOOPERHOST,
            commands,
            msg="Expected ERR_NOOPERHOST (491) in response to OPER with no password",
        )

        # Ensure RPL_YOUREOPER was NOT sent
        self.assertNotIn(
            RPL_YOUREOPER,
            commands,
            msg="RPL_YOUREOPER (381) should not be sent for OPER with no password",
        )

    @cases.mark_specifications("Ergo")
    def testOperNonexistentUser(self):
        """Test OPER command with nonexistent oper username."""
        self.connectClient("oper_user", name="oper_user")
        self.sendLine("oper_user", "OPER notanoperuser somepassword")
        messages = self.getMessages("oper_user")

        commands = {msg.command for msg in messages}
        self.assertIn(
            ERR_NOOPERHOST,
            commands,
            msg="Expected ERR_NOOPERHOST (491) in response to OPER with nonexistent username",
        )

        # Ensure RPL_YOUREOPER was NOT sent
        self.assertNotIn(
            RPL_YOUREOPER,
            commands,
            msg="RPL_YOUREOPER (381) should not be sent for OPER with nonexistent username",
        )
