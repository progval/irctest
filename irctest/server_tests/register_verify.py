from irctest import cases
from irctest.patma import ANYSTR

REGISTER_CAP_NAME = "draft/account-registration"


@cases.mark_specifications("IRCv3")
class TestRegisterBeforeConnect(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"]["registration"].update(
                {"allow-before-connect": True}
            )
        )

    def testBeforeConnect(self):
        self.addClient("bar")
        self.requestCapabilities("bar", [REGISTER_CAP_NAME], skip_if_cap_nak=True)
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertIn("before-connect", caps[REGISTER_CAP_NAME])
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        register_response = [msg for msg in msgs if msg.command == "REGISTER"][0]
        self.assertMessageMatch(register_response, params=["SUCCESS", ANYSTR, ANYSTR])


@cases.mark_specifications("IRCv3")
class TestRegisterBeforeConnectDisallowed(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"]["registration"].update(
                {"allow-before-connect": False}
            )
        )

    def testBeforeConnect(self):
        self.addClient("bar")
        self.requestCapabilities("bar", [REGISTER_CAP_NAME], skip_if_cap_nak=True)
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertEqual(caps[REGISTER_CAP_NAME], None)
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response,
            params=["REGISTER", "COMPLETE_CONNECTION_REQUIRED", ANYSTR, ANYSTR],
        )


@cases.mark_specifications("IRCv3")
class TestRegisterEmailVerified(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"]["registration"].update(
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
        )

    def testBeforeConnect(self):
        self.addClient("bar")
        self.requestCapabilities(
            "bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertEqual(
            set(caps[REGISTER_CAP_NAME].split(",")),
            {"before-connect", "email-required"},
        )
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response, params=["REGISTER", "INVALID_EMAIL", ANYSTR, ANYSTR]
        )

    def testAfterConnect(self):
        self.connectClient(
            "bar", name="bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response, params=["REGISTER", "INVALID_EMAIL", ANYSTR, ANYSTR]
        )


@cases.mark_specifications("IRCv3", "Ergo")
class TestRegisterNoLandGrabs(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"]["registration"].update(
                {"allow-before-connect": True}
            )
        )

    def testBeforeConnect(self):
        # have an anonymous client take the 'root' username:
        self.connectClient(
            "root", name="root", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )

        # cannot register it out from under the anonymous nick holder:
        self.addClient("bar")
        self.sendLine("bar", "NICK root")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response, params=["REGISTER", "USERNAME_EXISTS", ANYSTR, ANYSTR]
        )
