"""
`Ergo <https://ergo.chat/>`_-specific tests for nick collisions based on Unicode
confusable characters
"""

from irctest import cases
from irctest.numerics import ERR_NICKNAMEINUSE, RPL_WELCOME


@cases.mark_services
class ConfusablesTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["server"].update(
                {"casemapping": "precis"},
            )
        )

    @cases.mark_specifications("Ergo")
    def testConfusableNicks(self):
        self.controller.registerUser(self, "evan", "sesame")

        self.addClient(1)
        # U+0435 in place of e:
        self.sendLine(1, "NICK еvan")
        self.sendLine(1, "USER a 0 * a")
        messages = self.getMessages(1)
        commands = set(msg.command for msg in messages)
        self.assertNotIn(RPL_WELCOME, commands)
        self.assertIn(ERR_NICKNAMEINUSE, commands)

        self.connectClient(
            "evan", name="evan", password="sesame", capabilities=["sasl"]
        )
        # should be able to switch to the confusable nick
        self.sendLine("evan", "NICK еvan")
        messages = self.getMessages("evan")
        commands = set(msg.command for msg in messages)
        self.assertIn("NICK", commands)
