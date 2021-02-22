from irctest import cases

REGISTER_CAP_NAME = "draft/register"


class TestRegisterBeforeConnect(cases.BaseServerTestCase):
    @staticmethod
    def config():
        return {
            "oragono_config": lambda config: config["accounts"]["registration"].update(
                {"allow-before-connect": True}
            )
        }

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
    def testBeforeConnect(self):
        self.addClient("bar")
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertIn("before-connect", caps[REGISTER_CAP_NAME])
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * shivarampassphrase")
        msgs = self.getMessages("bar")
        register_response = [msg for msg in msgs if msg.command == "REGISTER"][0]
        self.assertEqual(register_response.params[0], "SUCCESS")


class TestRegisterBeforeConnectDisallowed(cases.BaseServerTestCase):
    @staticmethod
    def config():
        return {
            "oragono_config": lambda config: config["accounts"]["registration"].update(
                {"allow-before-connect": False}
            )
        }

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
    def testBeforeConnect(self):
        self.addClient("bar")
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertEqual(caps[REGISTER_CAP_NAME], None)
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertEqual(fail_response.params[:2], ["REGISTER", "DISALLOWED"])


class TestRegisterEmailVerified(cases.BaseServerTestCase):
    @staticmethod
    def config():
        return {
            "oragono_config": lambda config: config["accounts"]["registration"].update(
                {
                    "email-verification": {
                        "enabled": True,
                        "sender": "test@example.com",
                        "require-tls": True,
                        "helo-domain": "example.com",
                    },
                    "allow-before-connect": True,
                }
            )
        }

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
    def testBeforeConnect(self):
        self.addClient("bar")
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertEqual(
            set(caps[REGISTER_CAP_NAME].split(",")),
            {"before-connect", "email-required"},
        )
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertEqual(fail_response.params[:2], ["REGISTER", "INVALID_EMAIL"])

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
    def testAfterConnect(self):
        self.connectClient("bar", name="bar")
        self.sendLine("bar", "REGISTER * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertEqual(fail_response.params[:2], ["REGISTER", "INVALID_EMAIL"])


class TestRegisterNoLandGrabs(cases.BaseServerTestCase):
    @staticmethod
    def config():
        return {
            "oragono_config": lambda config: config["accounts"]["registration"].update(
                {"allow-before-connect": True}
            )
        }

    @cases.SpecificationSelector.requiredBySpecification("Oragono")
    def testBeforeConnect(self):
        # have an anonymous client take the 'root' username:
        self.connectClient("root", name="root")

        # cannot register it out from under the anonymous nick holder:
        self.addClient("bar")
        self.sendLine("bar", "NICK root")
        self.sendLine("bar", "REGISTER * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertEqual(fail_response.params[:2], ["REGISTER", "USERNAME_EXISTS"])
