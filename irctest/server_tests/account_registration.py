"""
`Draft IRCv3 account-registration
<https://ircv3.net/specs/extensions/account-registration>`_
"""

from irctest import cases
from irctest.patma import ANYSTR

REGISTER_CAP_NAME = "draft/account-registration"


@cases.mark_services
@cases.mark_specifications("IRCv3")
class RegisterTestCase(cases.BaseServerTestCase):
    def testRegisterDefaultName(self):
        """
        "If <account> is *, then this value is the user’s current nickname."
        """
        self.connectClient(
            "bar", name="bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertNotIn("email-required", (caps[REGISTER_CAP_NAME] or "").split(","))
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        register_response = [msg for msg in msgs if msg.command == "REGISTER"][0]
        self.assertMessageMatch(register_response, params=["SUCCESS", ANYSTR, ANYSTR])

    def testRegisterSameName(self):
        """
        Requested account name is the same as the nick
        """
        self.connectClient(
            "bar", name="bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertNotIn("email-required", (caps[REGISTER_CAP_NAME] or "").split(","))
        self.sendLine("bar", "REGISTER bar * shivarampassphrase")
        msgs = self.getMessages("bar")
        register_response = [msg for msg in msgs if msg.command == "REGISTER"][0]
        self.assertMessageMatch(register_response, params=["SUCCESS", ANYSTR, ANYSTR])

    def testRegisterDifferentName(self):
        """
        Requested account name differs from the nick
        """
        self.connectClient(
            "bar", name="bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertNotIn("email-required", (caps[REGISTER_CAP_NAME] or "").split(","))
        self.sendLine("bar", "REGISTER foo * shivarampassphrase")
        if "custom-account-name" in (caps[REGISTER_CAP_NAME] or "").split(","):
            msgs = self.getMessages("bar")
            register_response = [msg for msg in msgs if msg.command == "REGISTER"][0]
            self.assertMessageMatch(
                register_response, params=["SUCCESS", ANYSTR, ANYSTR]
            )
        else:
            self.assertMessageMatch(
                self.getMessage("bar"),
                command="FAIL",
                params=["REGISTER", "ACCOUNT_NAME_MUST_BE_NICK", "foo", ANYSTR],
            )


@cases.mark_services
@cases.mark_specifications("IRCv3")
class RegisterBeforeConnectTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            account_registration_requires_email=False,
            account_registration_before_connect=True,
        )

    def testBeforeConnect(self):
        self.addClient("bar")
        self.requestCapabilities("bar", [REGISTER_CAP_NAME], skip_if_cap_nak=True)
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertIn("before-connect", caps[REGISTER_CAP_NAME] or "")
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        register_response = [msg for msg in msgs if msg.command == "REGISTER"][0]
        self.assertMessageMatch(register_response, params=["SUCCESS", ANYSTR, ANYSTR])


@cases.mark_services
@cases.mark_specifications("IRCv3")
class RegisterBeforeConnectDisallowedTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            account_registration_requires_email=False,
            account_registration_before_connect=False,
        )

    def testBeforeConnect(self):
        self.addClient("bar")
        self.requestCapabilities("bar", [REGISTER_CAP_NAME], skip_if_cap_nak=True)
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertNotIn("before-connect", caps[REGISTER_CAP_NAME] or "")
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response,
            params=["REGISTER", "COMPLETE_CONNECTION_REQUIRED", ANYSTR, ANYSTR],
        )


@cases.mark_services
@cases.mark_specifications("IRCv3")
class RegisterEmailVerifiedBeforeConnectTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            account_registration_requires_email=True,
            account_registration_before_connect=True,
        )

    def testBeforeConnect(self):
        self.addClient("bar")
        self.requestCapabilities(
            "bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertIn("email-required", caps[REGISTER_CAP_NAME] or "")
        self.assertIn("before-connect", caps[REGISTER_CAP_NAME] or "")
        self.sendLine("bar", "NICK bar")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response, params=["REGISTER", "INVALID_EMAIL", ANYSTR, ANYSTR]
        )


@cases.mark_services
@cases.mark_specifications("IRCv3")
class RegisterEmailVerifiedAfterConnectTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            account_registration_before_connect=False,
            account_registration_requires_email=True,
        )

    def testAfterConnect(self):
        self.connectClient(
            "bar", name="bar", capabilities=[REGISTER_CAP_NAME], skip_if_cap_nak=True
        )
        self.sendLine("bar", "CAP LS 302")
        caps = self.getCapLs("bar")
        self.assertIn(REGISTER_CAP_NAME, caps)
        self.assertIn("email-required", caps[REGISTER_CAP_NAME] or "")
        self.sendLine("bar", "REGISTER * * shivarampassphrase")
        msgs = self.getMessages("bar")
        fail_response = [msg for msg in msgs if msg.command == "FAIL"][0]
        self.assertMessageMatch(
            fail_response, params=["REGISTER", "INVALID_EMAIL", ANYSTR, ANYSTR]
        )


@cases.mark_services
@cases.mark_specifications("IRCv3", "Ergo")
class RegisterNoLandGrabsTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            account_registration_requires_email=False,
            account_registration_before_connect=True,
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
