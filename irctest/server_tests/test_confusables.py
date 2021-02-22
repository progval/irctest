from irctest import cases
from irctest.numerics import ERR_NICKNAMEINUSE, RPL_WELCOME


class ConfusablesTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config():
        return {
            "oragono_config": lambda config: config["accounts"].update(
                {"nick-reservation": {"enabled": True, "method": "strict"}}
            )
        }

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
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

        self.connectClient("evan", name="evan", password="sesame")
        # should be able to switch to the confusable nick
        self.sendLine("evan", "NICK еvan")
        messages = self.getMessages("evan")
        commands = set(msg.command for msg in messages)
        self.assertIn("NICK", commands)
