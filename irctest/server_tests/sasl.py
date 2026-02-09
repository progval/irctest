import base64
import time

import pytest

from irctest import cases, runner, scram
from irctest.numerics import (
    ERR_ALREADYREGISTERED,
    ERR_INPUTTOOLONG,
    ERR_SASLABORTED,
    ERR_SASLALREADY,
    ERR_SASLFAIL,
    ERR_SASLTOOLONG,
    RPL_LOGGEDIN,
    RPL_SASLMECHS,
    RPL_SASLSUCCESS,
)
from irctest.patma import ANYLIST, ANYSTR, Either, StrRe
from irctest.specifications import OptionalBehaviors


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
            command=RPL_LOGGEDIN,
            params=[ANYSTR, ANYSTR, "jilles", ANYSTR],
            fail_msg="Unexpected reply to correct SASL authentication: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlainFailure(self):
        """PLAIN authentication with incorrect username/password."""
        self.controller.registerUser(self, "jilles", "sesame")
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
        # password 'millet'
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBtaWxsZXQ=")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=ERR_SASLFAIL,
            params=[ANYSTR, ANYSTR],
            fail_msg="Unexpected reply to incorrect SASL authentication: {msg}",
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
            command=RPL_LOGGEDIN,
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
            command=RPL_LOGGEDIN,
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
        while m.command == RPL_SASLMECHS:
            m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=ERR_SASLFAIL,
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

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    @cases.xfailIfSoftware(
        ["Ergo"],
        "Ergo has password length limits that prevent registering long passwords",
    )
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
    def testPlainLarge800(self):
        """Test AUTHENTICATE with exactly 800-byte payload (two 400-byte chunks).

        "If the last chunk was exactly 400 bytes long, it must also be followed
        by AUTHENTICATE + to signal end of response"
        -- <https://ircv3.net/specs/extensions/sasl-3.1#the-authenticate-command>
        """
        # We need a password that produces exactly 800 bytes of base64
        # base64 encoding: 3 bytes -> 4 chars, so 600 bytes -> 800 chars
        # authstring = base64(authzid \x00 authcid \x00 passwd)
        # With authzid="foo", authcid="foo", we have 3 + 1 + 3 + 1 = 8 bytes overhead
        # So password needs to be 600 - 8 = 592 bytes
        password = "x" * 592
        self.controller.registerUser(self, "foo", password)
        authstring = base64.b64encode(
            b"\x00".join([b"foo", b"foo", password.encode()])
        ).decode()
        self.assertEqual(len(authstring), 800, "Bad test: authstring should be 800")

        self.addClient()
        self.sendLine(1, "CAP LS 302")
        capabilities = self.getCapLs(1)
        self.assertIn("sasl", capabilities)
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # Send first 400 bytes
        self.sendLine(1, "AUTHENTICATE {}".format(authstring[0:400]))
        # Send second 400 bytes
        self.sendLine(1, "AUTHENTICATE {}".format(authstring[400:800]))
        # Must send AUTHENTICATE + to signal end since last chunk was exactly 400
        self.sendLine(1, "AUTHENTICATE +")

        self.confirmSuccessfulAuth()

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testSaslTooLong(self):
        """Tests that the server rejects AUTHENTICATE payloads over 400 bytes.

        "The response is encoded in Base64 (RFC 4648), then split to
        400-byte chunks"
        -- <https://ircv3.net/specs/extensions/sasl-3.1#the-authenticate-command>

        Servers should reply with 905 (ERR_SASLTOOLONG) if a single
        AUTHENTICATE parameter exceeds 400 bytes.
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # Send a single AUTHENTICATE with >400 bytes (not split properly)
        long_auth = "A" * 500
        self.sendLine(1, "AUTHENTICATE " + long_auth)
        m = self.getRegistrationMessage(1)
        # Server may reply with 905 (ERR_SASLTOOLONG) or 417 (ERR_INPUTTOOLONG)
        self.assertMessageMatch(
            m,
            command=Either(ERR_SASLTOOLONG, ERR_INPUTTOOLONG),
            params=["*", ANYSTR],
            fail_msg="Sent oversized AUTHENTICATE (500 bytes in one message), "
            "expected 905 (ERR_SASLTOOLONG) or 417 (ERR_INPUTTOOLONG), but got: {msg}",
        )

    def confirmSuccessfulAuth(self):
        # TODO: check username/etc in this as well, so we can apply it to other tests
        m1 = self.getRegistrationMessage(1)
        m2 = self.getRegistrationMessage(1)
        if m1.command == RPL_SASLSUCCESS and m2.command == RPL_LOGGEDIN:
            # Seems to happen only for Solanum with Anope.
            # Order is not guaranteed by the spec so this is fine
            (m1, m2) = (m2, m1)
        self.assertMessageMatch(
            m1,
            command=RPL_LOGGEDIN,
            fail_msg="Expected 900 (RPL_LOGGEDIN) after successful "
            "login, but got: {msg}",
        )
        self.assertMessageMatch(
            m2,
            command=RPL_SASLSUCCESS,
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

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testAbort(self):
        """Tests that the server sends 906 when client aborts authentication.

        "The client can abort an authentication by sending an asterisk as the
        data. The server will send a 906 numeric."
        -- <https://ircv3.net/specs/extensions/sasl-3.1#the-authenticate-command>
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        self.sendLine(1, "AUTHENTICATE *")
        m = self.getRegistrationMessage(1)
        # Server may reply with 906 (ERR_SASLABORTED) or 904 (ERR_SASLFAIL)
        self.assertMessageMatch(
            m,
            command=Either(ERR_SASLABORTED, ERR_SASLFAIL),
            params=["*", ANYSTR],
            fail_msg="Sent AUTHENTICATE * to abort, expected 906 (ERR_SASLABORTED) or "
            "904 (ERR_SASLFAIL), but got: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testInvalidBase64(self):
        """Tests that the server rejects invalid base64 in AUTHENTICATE."""
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # '!!!' is not valid base64
        self.sendLine(1, "AUTHENTICATE !!!")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=ERR_SASLFAIL,
            fail_msg="Sent invalid base64, expected 904 (ERR_SASLFAIL), "
            "but got: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testEmptyAuthcid(self):
        """Tests that authentication fails when authcid (username) is empty.

        "If preparation fails or results in an empty string, verification
        SHALL fail."
        -- <https://tools.ietf.org/html/rfc4616#section-2>
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # Empty authcid: base64("\x00\x00sesame")
        auth = base64.b64encode(b"\x00\x00sesame").decode()
        self.sendLine(1, "AUTHENTICATE " + auth)
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=ERR_SASLFAIL,
            fail_msg="Sent PLAIN auth with empty authcid, expected 904 "
            "(ERR_SASLFAIL), but got: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testEmptyPassword(self):
        """Tests that authentication fails when password is empty.

        "If preparation fails or results in an empty string, verification
        SHALL fail."
        -- <https://tools.ietf.org/html/rfc4616#section-2>
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # Empty password: base64("\x00jilles\x00")
        auth = base64.b64encode(b"\x00jilles\x00").decode()
        self.sendLine(1, "AUTHENTICATE " + auth)
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=ERR_SASLFAIL,
            fail_msg="Sent PLAIN auth with empty password, expected 904 "
            "(ERR_SASLFAIL), but got: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testDifferentAuthzid(self):
        """Tests authentication with different authzid and authcid.

        "The server will [...] verify that the authentication credentials permit
        the client to act as the (presented or derived) authorization identity
        (authzid)."
        -- <https://tools.ietf.org/html/rfc4616#section-2>

        This should fail unless the server allows authorization identity
        impersonation.
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.controller.registerUser(self, "other", "password")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # authzid=other, authcid=jilles, passwd=sesame
        # jilles is trying to authorize as "other"
        auth = base64.b64encode(b"other\x00jilles\x00sesame").decode()
        self.sendLine(1, "AUTHENTICATE " + auth)
        m = self.getRegistrationMessage(1)
        # Most servers should reject this (904) since jilles cannot act as other.
        # Some servers might allow it if they support authzid impersonation.
        self.assertMessageMatch(
            m,
            command=Either(ERR_SASLFAIL, RPL_LOGGEDIN),
            params=["*", *ANYLIST],
            fail_msg="Sent PLAIN auth with different authzid/authcid, expected "
            "either 904 (ERR_SASLFAIL) or 900 (RPL_LOGGEDIN), but got: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testAuthenticateWithoutCapReq(self):
        """Tests that AUTHENTICATE without CAP REQ sasl is handled gracefully.

        Some servers may allow AUTHENTICATE without first requesting the sasl
        capability. This test verifies the server handles this case without
        crashing or misbehaving.
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)
        # Don't request sasl capability, just try to authenticate
        self.sendLine(1, "AUTHENTICATE PLAIN")
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER foo 0 * :foo")
        self.sendLine(1, "CAP END")
        # Server may either ignore AUTHENTICATE, send an error, or proceed.
        # We just verify it handles this gracefully (doesn't crash).
        self.getMessages(1)
        # Either way, we should be able to get messages without error.
        # The server may have responded with AUTHENTICATE + or ignored it.
        # This test mainly ensures graceful handling.

    @cases.mark_specifications("IRCv3")
    @pytest.mark.parametrize(
        "strict",
        [
            pytest.param(False, id="non-strict"),
            pytest.param(True, id="strict", marks=pytest.mark.strict),
        ],
    )
    def testSaslMechsContent(self, strict):
        """Tests that 908 RPL_SASLMECHS contains a valid mechanism list.

        "RPL_SASLMECHS MAY be sent in reply to an AUTHENTICATE command which
        requests an unsupported mechanism."
        -- <https://ircv3.net/specs/extensions/sasl-3.1#numerics-used-by-this-extension>

        "The numeric contains a comma-separated list of mechanisms supported
        by the server (or network, services).
        :server 908 <nick> <mechanisms> :are available SASL mechanisms"
        -- <https://ircv3.net/specs/extensions/sasl-3.1#numerics-used-by-this-extension>

        "sasl-mech    = 1*20mech-char
        mech-char    = UPPER-ALPHA / DIGIT / HYPHEN / UNDERSCORE"
        -- https://datatracker.ietf.org/doc/html/rfc4422#section-3.1

        The 20-char limit is not enforced unless in strict mode, as
        ``ECDSA-NIST256P-CHALLENGE`` is common on IRC and blessed by IANA.
        """
        if not self.controller.supported_sasl_mechanisms:
            raise runner.CapabilityNotSupported("sasl")

        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE UNSUPPORTED_MECH")
        messages = []
        for _ in range(3):
            m = self.getRegistrationMessage(1)
            messages.append(m)
            if m.command == ERR_SASLFAIL:
                break
        # Look for 908 in the response
        saslmechs = [m for m in messages if m.command == RPL_SASLMECHS]
        if saslmechs:
            # Verify the format: 908 <nick> <mechanisms> :are available mechanisms
            (m,) = saslmechs
            if strict:
                self.assertMessageMatch(
                    m,
                    command=RPL_SASLMECHS,
                    params=[
                        "*",
                        StrRe("([A-Z0-9_-]{1,20})(,[A-Z0-9_-]{1,20})*"),
                        ANYSTR,
                    ],
                )
            else:
                # ECDSA-NIST256P-CHALLENGE is common on IRC and blessed by IANA,
                # but is invalid according to RFC4422
                self.assertMessageMatch(
                    m,
                    command=RPL_SASLMECHS,
                    params=["*", StrRe("([A-Z0-9_-]+)(,[A-Z0-9_-]+)*"), ANYSTR],
                )

    @pytest.mark.xfail(reason="the RFC does not say servers have to reject it")
    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    @pytest.mark.parametrize(
        "password", ["sesa\x00me", "sesame\x00", "sesame\x00extra"]
    )
    def testNulInPassword(self, password):
        """Tests that authentication fails when password contains NUL.

        NUL is disallowed in authcid/authzid/passwd (https://tools.ietf.org/html/rfc4616#section-2)
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # Password with embedded NUL: "sesa\x00me"
        # This creates: \x00jilles\x00sesa\x00me which has 4 parts instead of 3
        auth = base64.b64encode(b"\x00jilles\x00" + password.encode()).decode()
        self.sendLine(1, "AUTHENTICATE " + auth)
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=ERR_SASLFAIL,
            fail_msg="Sent PLAIN auth with NUL in password, expected 904 "
            "(ERR_SASLFAIL), but got: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testNickUserDuringSasl(self):
        """NICK and USER within a SASL session should not abort SASL"""
        self.controller.registerUser(self, "jilles", "sesame")
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
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER foo * * :Test")
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command=RPL_LOGGEDIN,
            params=[ANYSTR, ANYSTR, "jilles", ANYSTR],
            fail_msg="Unexpected reply to correct SASL authentication: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testRegistrationDuringSasl(self):
        """Tests that the server handles registration during SASL gracefully.

        "If the client completes registration (with CAP END, NICK, USER and any other
        necessary messages) while the SASL authentication is still in progress,
        the server SHOULD abort it and send a 906 numeric, then register the client
        without authentication."
        -- <https://ircv3.net/specs/extensions/sasl-3.1>
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
        )
        # Instead of completing SASL, complete registration
        self.sendLine(1, "NICK reguser")
        self.sendLine(1, "USER reguser 0 * :Test")
        self.sendLine(1, "CAP END")
        # Server should abort SASL (906) and complete registration
        messages = self.getMessages(1)
        commands = {m.command for m in messages}
        # Should either get 906 or just complete registration
        # Check that we got either 906 or welcome (001)
        if ERR_SASLABORTED not in commands and "001" not in commands:
            self.fail(
                "Expected either 906 (ERR_SASLABORTED) or 001 (RPL_WELCOME), "
                f"got: {[m.command for m in messages]}"
            )

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testRetryAfterInvalidBase64(self):
        """Tests that authentication can be retried after failure.

        "If authentication fails, a 904 or 905 numeric will be sent and the
        client MAY retry from the AUTHENTICATE <mechanism> command."
        -- <https://ircv3.net/specs/extensions/sasl-3.1#the-authenticate-command>
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)

        # First attempt: invalid base64
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command="AUTHENTICATE", params=["+"])
        self.sendLine(1, "AUTHENTICATE !!!")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command=ERR_SASLFAIL, params=["*", ANYSTR])

        # Second attempt: correct password
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="After SASL failure, client should be able to retry. "
            "Server should reply with AUTHENTICATE +, but got: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        self.confirmSuccessfulAuth()

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testRetryAfterFail(self):
        """Tests that authentication can be retried after failure.

        "If authentication fails, a 904 or 905 numeric will be sent and the
        client MAY retry from the AUTHENTICATE <mechanism> command."
        -- <https://ircv3.net/specs/extensions/sasl-3.1#the-authenticate-command>
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.addClient()
        self.requestCapabilities(1, ["sasl"], skip_if_cap_nak=False)

        # First attempt: wrong password ("millet" instead of "sesame")
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command="AUTHENTICATE", params=["+"])
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBtaWxsZXQ=")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command=ERR_SASLFAIL, params=["*", ANYSTR])

        # Second attempt: correct password
        self.sendLine(1, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="After SASL failure, client should be able to retry. "
            "Server should reply with AUTHENTICATE +, but got: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        self.confirmSuccessfulAuth()

    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlainPostRegistration(self):
        """
        "Servers SHOULD allow a client, authenticated or otherwise, to reauthenticate by sending
        a new AUTHENTICATE message at any time."
        -- https://ircv3.net/specs/extensions/sasl-3.2
        """
        self.controller.registerUser(self, "jilles", "sesame")

        self.connectClient("foo", capabilities=["sasl"], skip_if_cap_nak=True)

        self.sendLine(1, "AUTHENTICATE PLAIN")
        time.sleep(2)
        m = self.getMessage(1)
        if m.command == ERR_ALREADYREGISTERED:
            raise runner.OptionalBehaviorNotSupported(
                OptionalBehaviors.SASL_AFTER_REGISTRATION
            )
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        self.confirmSuccessfulAuth()

    @cases.xfailIfSoftware(
        ["Atheme"],
        "Atheme sends spurious RPL_LOGGEDOUT before RPL_LOGGEDIN when reauthenticating: "
        "https://github.com/atheme/atheme/issues/952",
    )
    @cases.xfailIfSoftware(
        ["Dlk"],
        "Dlk-Services crashes when reauthenticating and the initial authentication happened "
        "after registration: https://github.com/DalekIRC/Dalek-Services/issues/59",
    )
    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlainPostRegistrationAndReAuthenticate(self):
        """
        "Servers SHOULD allow a client, authenticated or otherwise, to reauthenticate by sending
        a new AUTHENTICATE message at any time."
        -- https://ircv3.net/specs/extensions/sasl-3.2
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.controller.registerUser(self, "foo", "bar")

        self.connectClient("user", capabilities=["sasl"], skip_if_cap_nak=True)

        # authenticate as foo
        authstring = base64.b64encode(b"\x00".join([b"foo", b"foo", b"bar"])).decode()
        self.sendLine(1, "AUTHENTICATE PLAIN")
        time.sleep(2)
        m = self.getMessage(1)
        if m.command == ERR_ALREADYREGISTERED:
            raise runner.OptionalBehaviorNotSupported(
                OptionalBehaviors.SASL_AFTER_REGISTRATION
            )
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE " + authstring)
        self.confirmSuccessfulAuth()

        # reauthenticate as jilles
        self.sendLine(1, "AUTHENTICATE PLAIN")
        time.sleep(2)
        m = self.getMessage(1)
        if m.command == ERR_SASLALREADY:
            self.assertMessageMatch(
                m,
                command=ERR_SASLALREADY,
                params=["user", ANYSTR],
                fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
                "replied with “AUTHENTICATE +” or 907 (ERR_SASLALREADY), "
                "but instead sent: {msg}",
            )
            raise runner.OptionalBehaviorNotSupported(
                OptionalBehaviors.SASL_REAUTHENTICATION
            )
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        self.confirmSuccessfulAuth()

    @cases.xfailIfSoftware(
        ["Atheme"],
        "Atheme sends spurious RPL_LOGGEDOUT before RPL_LOGGEDIN when reauthenticating: "
        "https://github.com/atheme/atheme/issues/952",
    )
    @cases.mark_specifications("IRCv3")
    @cases.skipUnlessHasMechanism("PLAIN")
    def testPlainReAuthenticate(self):
        """
        "Servers SHOULD allow a client, authenticated or otherwise, to reauthenticate by sending
        a new AUTHENTICATE message at any time."
        -- https://ircv3.net/specs/extensions/sasl-3.2
        """
        self.controller.registerUser(self, "jilles", "sesame")
        self.controller.registerUser(self, "foo", "bar")

        self.connectClient(
            "user",
            capabilities=["sasl"],
            skip_if_cap_nak=True,
            account="foo",
            password="bar",
        )

        # reauthenticate as jilles
        self.sendLine(1, "AUTHENTICATE PLAIN")
        time.sleep(2)
        m = self.getMessage(1)
        if m.command == ERR_ALREADYREGISTERED:
            raise runner.OptionalBehaviorNotSupported(
                OptionalBehaviors.SASL_AFTER_REGISTRATION
            )
        elif m.command == ERR_SASLALREADY:
            self.assertMessageMatch(
                m,
                command=ERR_SASLALREADY,
                params=["user", ANYSTR],
                fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
                "replied with “AUTHENTICATE +” or 907 (ERR_SASLALREADY), "
                "but instead sent: {msg}",
            )
            raise runner.OptionalBehaviorNotSupported(
                OptionalBehaviors.SASL_REAUTHENTICATION
            )
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(1, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        self.confirmSuccessfulAuth()
