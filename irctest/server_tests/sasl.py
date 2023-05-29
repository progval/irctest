import base64

from irctest import cases, runner, scram
from irctest.numerics import ERR_SASLFAIL
from irctest.patma import ANYSTR


@cases.mark_services
class RegistrationTestCase(cases.BaseServerTestCase):
    def testRegistration(self):
        self.controller.registerUser(self, "testuser", "mypassword")


@cases.mark_services
class SaslTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlain(self):
        """PLAIN authentication with correct username/password."""
        self.controller.registerUser(self, "foo", "sesame")
        self.controller.registerUser(self, "jilles", "sesame")
        self.controller.registerUser(self, "bar", "sesame")
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        if capabilities["sasl"] is not None:
            self.assertIn(
                "PLAIN",
                capabilities["sasl"],
                fail_msg="Does not have PLAIN mechanism as the controller " "claims",
            )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="900",
            params=[ANYSTR, ANYSTR, "jilles", ANYSTR],
            fail_msg="Unexpected reply to correct SASL authentication: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlainNonAscii(self):
        password = "é" * 100
        authstring = base64.b64encode(
            b"\x00".join([b"foo", b"foo", password.encode()])
        ).decode()
        self.controller.registerUser(self, "foo", password)
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE " + authstring)
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="900",
            params=[ANYSTR, ANYSTR, "foo", ANYSTR],
            fail_msg="Unexpected reply to correct SASL authentication: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlainNoAuthzid(self):
        """“message   = [authzid] UTF8NUL authcid UTF8NUL passwd

        […]

        Upon receipt of the message, the server will verify the presented (in
        the message) authentication identity (authcid) and password (passwd)
        with the system authentication database, and it will verify that the
        authentication credentials permit the client to act as the (presented
        or derived) authorization identity (authzid).  If both steps succeed,
        the user is authenticated.

        […]


        When no authorization identity is provided, the server derives an
        authorization identity from the prepared representation of the
        provided authentication identity string.  This ensures that the
        derivation of different representations of the authentication
        identity produces the same authorization identity.”
        -- <https://tools.ietf.org/html/rfc4616#section-2>
        """
        self.controller.registerUser(self, "foo", "sesame")
        self.controller.registerUser(self, "jilles", "sesame")
        self.controller.registerUser(self, "bar", "sesame")
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        if capabilities["sasl"] is not None:
            self.assertIn(
                "PLAIN",
                capabilities["sasl"],
                fail_msg="Does not have PLAIN mechanism as the controller " "claims",
            )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE AGppbGxlcwBzZXNhbWU=")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="900",
            params=[ANYSTR, ANYSTR, "jilles", ANYSTR],
            fail_msg="Unexpected reply to correct SASL authentication: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    def testMechanismNotAvailable(self):
        """“If authentication fails, a 904 or 905 numeric will be sent”
        -- <http://ircv3.net/specs/extensions/sasl-3.1.html#the-authenticate-command>
        """
        if not self.controller.supported_sasl_mechanisms:
            raise runner.CapabilityNotSupported("sasl")

        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE FOO")
        m = self.getRegistrationMessage(1)
        while m.command == "908":  # RPL_SASLMECHS
            m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="904",
            fail_msg="Did not reply with 904 to “AUTHENTICATE FOO”: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    @cases.xfailIf(
        lambda self: (
            self.controller.services_controller is not None
            and self.controller.services_controller.software_name == "Anope"
        ),
        "Anope does not handle split AUTHENTICATE (reported on IRC)",
    )
    @cases.xfailIf(
        lambda self: (
            self.controller.services_controller is not None
            and self.controller.services_controller.software_name == "Dlk-Services"
        ),
        "Dlk does not handle split AUTHENTICATE "
        "https://github.com/DalekIRC/Dalek-Services/issues/28",
    )
    def testPlainLarge(self):
        """Test the client splits large AUTHENTICATE messages whose payload
        is not a multiple of 400.
        <http://ircv3.net/specs/extensions/sasl-3.1.html#the-authenticate-command>
        """
        self.controller.registerUser(self, "foo", "bar" * 100)
        authstring = base64.b64encode(
            b"\x00".join([b"foo", b"foo", b"bar" * 100])
        ).decode()
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        if capabilities["sasl"] is not None:
            self.assertIn(
                "PLAIN",
                capabilities["sasl"],
                fail_msg="Does not have PLAIN mechanism as the controller " "claims",
            )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, expected "
            "“AUTHENTICATE +” as a response, but got: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE {}".format(authstring[0:400]))
        self.sendLine(1, "AUTHENTICATE {}".format(authstring[400:]))

        self.confirmSuccessfulAuth()

    def confirmSuccessfulAuth(self):
        # TODO: check username/etc in this as well, so we can apply it to other tests
        # TODO: may be in the other order
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="900",
            fail_msg="Expected 900 (RPL_LOGGEDIN) after successful "
            "login, but got: {msg}",
        )
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="903",
            fail_msg="Expected 903 (RPL_SASLSUCCESS) after successful "
            "login, but got: {msg}",
        )

    # TODO: add a test for when the length of the authstring is greater than 800.
    # I don't know how to do it, because it would make the registration
    # message's length too big for it to be valid.

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    @cases.xfailIf(
        lambda self: (
            self.controller.services_controller is not None
            and self.controller.services_controller.software_name == "Anope"
        ),
        "Anope does not handle split AUTHENTICATE (reported on IRC)",
    )
    def testPlainLargeEquals400(self):
        """Test the client splits large AUTHENTICATE messages whose payload
        is not a multiple of 400.
        <http://ircv3.net/specs/extensions/sasl-3.1.html#the-authenticate-command>
        """
        self.controller.registerUser(self, "foo", "bar" * 97)
        authstring = base64.b64encode(
            b"\x00".join([b"foo", b"foo", b"bar" * 97])
        ).decode()
        assert len(authstring) == 400, "Bad test"
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        if capabilities["sasl"] is not None:
            self.assertIn(
                "PLAIN",
                capabilities["sasl"],
                fail_msg="Does not have PLAIN mechanism as the controller " "claims",
            )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, expected "
            "“AUTHENTICATE +” as a response, but got: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE {}".format(authstring))
        self.sendLine(1, "AUTHENTICATE +")

        self.confirmSuccessfulAuth()

    # TODO: add a test for when the length of the authstring is 800.
    # I don't know how to do it, because it would make the registration
    # message's length too big for it to be valid.

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("SCRAM-SHA-256")
    def testScramSha256Success(self):
        self.controller.registerUser(self, "Scramtest", "sesame")

        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        if capabilities["sasl"] is not None:
            self.assertIn(
                "SCRAM-SHA-256",
                capabilities["sasl"],
                fail_msg="Does not have SCRAM-SHA-256 mechanism as the "
                "controller claims",
            )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)

        self.sendLine(1, "AUTHENTICATE SCRAM-SHA-256")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE SCRAM-SHA-256”, expected "
            "“AUTHENTICATE +” as a response, but got: {msg}",
        )

        authenticator = scram.SCRAMClientAuthenticator("SHA-256", False)
        first_message = authenticator.start(
            {
                "username": "Scramtest",
                "password": "sesame",
            }
        )
        self.sendLine(
            1, "AUTHENTICATE " + base64.b64encode(first_message).decode("ascii")
        )
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command="AUTHENTICATE")
        second_message = authenticator.challenge(base64.b64decode(m.params[0]))
        self.sendLine(
            1, "AUTHENTICATE " + base64.b64encode(second_message).decode("ascii")
        )
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command="AUTHENTICATE")
        # test the server's attempt to authenticate to us:
        result = authenticator.finish(base64.b64decode(m.params[0]))
        self.assertEqual(result["username"], "Scramtest")
        self.sendLine(1, "AUTHENTICATE +")
        self.confirmSuccessfulAuth()

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("SCRAM-SHA-256")
    def testScramSha256Failure(self):
        self.controller.registerUser(self, "Scramtest", "sesame")

        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn(
            "sasl",
            capabilities,
            fail_msg="Does not have SASL as the controller claims.",
        )
        if capabilities["sasl"] is not None:
            self.assertIn(
                "SCRAM-SHA-256",
                capabilities["sasl"],
                fail_msg="Does not have SCRAM-SHA-256 mechanism as the "
                "controller claims",
            )
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)

        self.sendLine(1, "AUTHENTICATE SCRAM-SHA-256")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE SCRAM-SHA-256”, expected "
            "“AUTHENTICATE +” as a response, but got: {msg}",
        )

        authenticator = scram.SCRAMClientAuthenticator("SHA-256", False)
        first_message = authenticator.start(
            {
                "username": "Scramtest",
                "password": "millet",
            }
        )
        self.sendLine(
            1, "AUTHENTICATE " + base64.b64encode(first_message).decode("ascii")
        )
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command="AUTHENTICATE")
        second_message = authenticator.challenge(base64.b64decode(m.params[0]))
        self.sendLine(
            1, "AUTHENTICATE " + base64.b64encode(second_message).decode("ascii")
        )
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command=ERR_SASLFAIL)
