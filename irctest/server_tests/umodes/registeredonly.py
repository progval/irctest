"""
Test the registered-only DM user mode (commonly +R).
"""

from irctest import cases
from irctest.numerics import ERR_NEEDREGGEDNICK


@cases.mark_services
class RegisteredOnlyUmodeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testRegisteredOnlyUserMode(self):
        """Test the +R registered-only mode."""
        self.controller.registerUser(self, "evan", "sesame")
        self.controller.registerUser(self, "carmen", "pink")

        self.connectClient(
            "evan",
            name="evan",
            account="evan",
            password="sesame",
            capabilities=["sasl"],
        )
        self.connectClient("shivaram", name="shivaram")
        self.sendLine("evan", "MODE evan +R")
        self.assertMessageMatch(
            self.getMessage("evan"), command="MODE", params=["evan", "+R"]
        )

        # this DM should be blocked by +R registered-only
        self.getMessages("shivaram")
        self.sendLine("shivaram", "PRIVMSG evan :hey there")
        self.assertMessageMatch(
            self.getMessage("shivaram"),
            command=ERR_NEEDREGGEDNICK,
        )
        self.assertEqual(self.getMessages("evan"), [])

        self.connectClient(
            "carmen",
            name="carmen",
            account="carmen",
            password="pink",
            capabilities=["sasl"],
        )
        self.getMessages("evan")
        self.sendLine("carmen", "PRIVMSG evan :hey there")
        self.assertEqual(self.getMessages("carmen"), [])
        # this message should go through fine:
        self.assertMessageMatch(
            self.getMessage("evan"),
            command="PRIVMSG",
            params=["evan", "hey there"],
        )

    @cases.mark_specifications("Ergo")
    def testRegisteredOnlyUserModeAcceptCommand(self):
        """Test that the ACCEPT command can authorize another user
        to send the accept-er direct messages, overriding the
        +R registered-only mode."""
        self.controller.registerUser(self, "evan", "sesame")
        self.connectClient(
            "evan",
            name="evan",
            account="evan",
            password="sesame",
            capabilities=["sasl"],
        )
        self.connectClient("shivaram", name="shivaram")
        self.sendLine("evan", "MODE evan +R")
        self.assertMessageMatch(
            self.getMessage("evan"), command="MODE", params=["evan", "+R"]
        )
        self.sendLine("evan", "ACCEPT shivaram")
        self.getMessages("evan")

        self.sendLine("shivaram", "PRIVMSG evan :hey there")
        self.assertEqual(self.getMessages("shivaram"), [])
        self.assertMessageMatch(
            self.getMessage("evan"),
            command="PRIVMSG",
            params=["evan", "hey there"],
        )

        self.sendLine("evan", "ACCEPT -shivaram")
        self.getMessages("evan")
        self.sendLine("shivaram", "PRIVMSG evan :how's it going")
        self.assertMessageMatch(
            self.getMessage("shivaram"),
            command=ERR_NEEDREGGEDNICK,
        )
        self.assertEqual(self.getMessages("evan"), [])

    @cases.mark_specifications("Ergo")
    def testRegisteredOnlyUserModeAutoAcceptOnDM(self):
        """Test that sending someone a DM automatically authorizes them to
        reply, overriding the +R registered-only mode."""
        self.controller.registerUser(self, "evan", "sesame")
        self.connectClient(
            "evan",
            name="evan",
            account="evan",
            password="sesame",
            capabilities=["sasl"],
        )
        self.connectClient("shivaram", name="shivaram")
        self.sendLine("evan", "MODE evan +R")
        self.assertMessageMatch(
            self.getMessage("evan"), command="MODE", params=["evan", "+R"]
        )
        self.sendLine("evan", "PRIVMSG shivaram :hey there")
        self.getMessages("evan")
        self.assertMessageMatch(
            self.getMessage("shivaram"),
            command="PRIVMSG",
            params=["shivaram", "hey there"],
        )
        self.sendLine("shivaram", "PRIVMSG evan :how's it going")
        self.assertEqual(self.getMessages("shivaram"), [])
        self.assertMessageMatch(
            self.getMessage("evan"),
            command="PRIVMSG",
            params=["evan", "how's it going"],
        )
