"""
Tests section 4.1 of RFC 1459.
<https://tools.ietf.org/html/rfc1459#section-4.1>

TODO: cross-reference Modern and RFC 2812 too
"""

from irctest import cases
from irctest.client_mock import ConnectionClosed
from irctest.numerics import ERR_NEEDMOREPARAMS, ERR_PASSWDMISMATCH
from irctest.patma import ANYSTR, StrRe


class PasswordedConnectionRegistrationTestCase(cases.BaseServerTestCase):
    password = "testpassword"

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testPassBeforeNickuser(self):
        self.addClient()
        self.sendLine(1, "PASS {}".format(self.password))
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER username * * :Realname")

        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="001",
            fail_msg="Did not get 001 after correct PASS+NICK+USER: {msg}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testNoPassword(self):
        self.addClient()
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER username * * :Realname")
        m = self.getRegistrationMessage(1)
        self.assertNotEqual(
            m.command, "001", msg="Got 001 after NICK+USER but missing PASS"
        )

    @cases.mark_specifications("Modern")
    def testWrongPassword(self):
        """
        "If the password supplied does not match the password expected by the server,
        then the server SHOULD send ERR_PASSWDMISMATCH and MUST close the connection
        with ERROR."
        -- https://github.com/ircdocs/modern-irc/pull/172
        """
        self.addClient()
        self.sendLine(1, "PASS {}".format(self.password + "garbage"))
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER username * * :Realname")
        m = self.getRegistrationMessage(1)
        self.assertNotEqual(
            m.command, "001", msg="Got 001 after NICK+USER but incorrect PASS"
        )
        self.assertIn(m.command, {ERR_PASSWDMISMATCH, "ERROR"})

        if m.command == "ERR_PASSWDMISMATCH":
            m = self.getRegistrationMessage(1)
            self.assertEqual(
                m.command, "ERROR", msg="ERR_PASSWDMISMATCH not followed by ERROR."
            )

    @cases.mark_specifications("RFC1459", "RFC2812", strict=True)
    def testPassAfterNickuser(self):
        """“The password can and must be set before any attempt to register
        the connection is made.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.1.1>

        “The optional password can and MUST be set before any attempt to
        register the connection is made.
        Currently this requires that user send a PASS command before
        sending the NICK/USER combination.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.1.1>
        """
        self.addClient()
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER username * * :Realname")
        self.sendLine(1, "PASS {}".format(self.password))
        m = self.getRegistrationMessage(1)
        self.assertNotEqual(m.command, "001", "Got 001 after PASS sent after NICK+USER")


class ConnectionRegistrationTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459")
    def testQuitDisconnects(self):
        """“The server must close the connection to a client which sends a
        QUIT message.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.1.3>
        """
        self.connectClient("foo")
        self.getMessages(1)
        self.sendLine(1, "QUIT")
        with self.assertRaises(ConnectionClosed):
            self.getMessages(1)  # Fetch remaining messages
            self.getMessages(1)

    @cases.mark_specifications("RFC2812")
    @cases.xfailIfSoftware(["Charybdis", "Solanum"], "very flaky")
    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "snircd"], "ircu2 does not send ERROR"
    )
    def testQuitErrors(self):
        """“A client session is terminated with a quit message.  The server
        acknowledges this by sending an ERROR message to the client.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.1.7>
        """
        self.connectClient("foo")
        self.getMessages(1)
        self.sendLine(1, "QUIT")
        while True:
            try:
                new_messages = self.getMessages(1)
                if not new_messages:
                    break
                commands = {m.command for m in new_messages}
            except ConnectionClosed:
                break
        self.assertIn(
            "ERROR", commands, fail_msg="Did not receive ERROR as a reply to QUIT."
        )

    def testNickCollision(self):
        """A user connects and requests the same nickname as an already
        registered user.
        """
        self.connectClient("foo")
        self.addClient()
        self.sendLine(2, "NICK foo")
        self.sendLine(2, "USER username * * :Realname")
        m = self.getRegistrationMessage(2)
        self.assertNotEqual(
            m.command,
            "001",
            "Received 001 after registering with the nick of a " "registered user.",
        )

    def testEarlyNickCollision(self):
        """Two users register simultaneously with the same nick."""
        self.addClient()
        self.addClient()
        self.sendLine(1, "NICK foo")
        self.sendLine(2, "NICK foo")
        self.sendLine(1, "USER username * * :Realname")

        try:
            self.sendLine(2, "USER username * * :Realname")
        except (ConnectionClosed, ConnectionResetError):
            # Bahamut closes the connection here
            pass

        try:
            m1 = self.getRegistrationMessage(1)
        except (ConnectionClosed, ConnectionResetError):
            # Unreal closes the connection, see
            # https://bugs.unrealircd.org/view.php?id=5950
            command1 = None
        else:
            command1 = m1.command

        try:
            m2 = self.getRegistrationMessage(2)
        except (ConnectionClosed, ConnectionResetError):
            # ditto
            command2 = None
        else:
            command2 = m2.command

        self.assertNotEqual(
            (command1, command2),
            ("001", "001"),
            "Two concurrently registering requesting the same nickname "
            "both got 001.",
        )

        self.assertIn(
            "001",
            (command1, command2),
            "Two concurrently registering requesting the same nickname "
            "neither got 001.",
        )

    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "ngIRCd"],
        "uses a default value instead of ERR_NEEDMOREPARAMS",
    )
    def testEmptyRealname(self):
        """
        Syntax:
        "<client> <command> :Not enough parameters"
        -- https://defs.ircdocs.horse/defs/numerics.html#err-needmoreparams-461
        -- https://modern.ircdocs.horse/#errneedmoreparams-461

        Use of this numeric:
        "The minimum length of `<username>` is 1, ie. it MUST not be empty.
        If it is empty, the server SHOULD reject the command with ERR_NEEDMOREPARAMS
        (even an empty parameter is provided)"
        https://github.com/ircdocs/modern-irc/issues/85
        """
        self.addClient()
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER username * * :")
        self.assertMessageMatch(
            self.getRegistrationMessage(1),
            command=ERR_NEEDMOREPARAMS,
            params=[StrRe(r"(\*|foo)"), "USER", ANYSTR],
        )
