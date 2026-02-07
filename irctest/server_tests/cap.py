"""
`IRCv3 Capability negotiation
<https://ircv3.net/specs/extensions/capability-negotiation>`_
"""

from irctest import cases
from irctest.patma import ANYSTR, StrRe
from irctest.runner import CapabilityNotSupported, OptionalBehaviorNotSupported
from irctest.specifications import OptionalBehaviors


class CapTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("IRCv3")
    def testInvalidCapSubcommand(self):
        """“If no capabilities are active, an empty parameter must be sent.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-list-subcommand>
        """  # noqa
        self.addClient()
        self.sendLine(1, "CAP NOTACOMMAND")
        self.sendLine(1, "PING test123")
        m = self.getRegistrationMessage(1)
        self.assertTrue(
            self.messageDiffers(m, command="PONG", params=[ANYSTR, "test123"]),
            "Sending “CAP NOTACOMMAND” as first message got no reply",
        )
        self.assertMessageMatch(
            m,
            command="410",
            params=["*", "NOTACOMMAND", ANYSTR],
            fail_msg="Sending “CAP NOTACOMMAND” as first message got a reply "
            "that is not ERR_INVALIDCAPCMD: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    def testNoReq(self):
        """Test the server handles gracefully clients which do not send
        REQs.

        “Clients that support capabilities but do not wish to enter
        negotiation SHOULD send CAP END upon connection to the server.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-end-subcommand>
        """  # noqa
        self.addClient(1)
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")

        # Make sure the server didn't send anything yet
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)

        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
        )

    @cases.mark_specifications("IRCv3")
    def testReqOne(self):
        """Tests requesting a single capability"""
        self.addClient(1)
        self.sendLine(1, "CAP LS")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "CAP REQ :multi-prefix")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("multi-prefix ?")],
            fail_msg="Expected CAP ACK after sending CAP REQ, got {msg}.",
        )

        self.sendLine(1, "CAP LIST")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "LIST", StrRe("multi-prefix ?")],
            fail_msg="Expected CAP LIST after sending CAP LIST, got {msg}.",
        )

        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
        )

    @cases.mark_specifications("IRCv3")
    @cases.xfailIfSoftware(
        ["ngIRCd"],
        "does not support userhost-in-names",
    )
    def testReqTwo(self):
        """Tests requesting two capabilities at once"""
        self.addClient(1)
        self.sendLine(1, "CAP LS")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "CAP REQ :multi-prefix userhost-in-names")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("multi-prefix userhost-in-names ?")],
            fail_msg="Expected CAP ACK after sending CAP REQ, got {msg}.",
        )

        self.sendLine(1, "CAP LIST")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[
                ANYSTR,
                "LIST",
                StrRe(
                    "(multi-prefix userhost-in-names|userhost-in-names multi-prefix) ?"
                ),
            ],
            fail_msg="Expected CAP LIST after sending CAP LIST, got {msg}.",
        )

        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
        )

    @cases.mark_specifications("IRCv3")
    @cases.xfailIfSoftware(
        ["ngIRCd"],
        "does not support userhost-in-names",
    )
    def testReqOneThenOne(self):
        """Tests requesting two capabilities in different messages"""
        self.addClient(1)
        self.sendLine(1, "CAP LS")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")

        self.sendLine(1, "CAP REQ :multi-prefix")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("multi-prefix ?")],
            fail_msg="Expected CAP ACK after sending CAP REQ, got {msg}.",
        )

        self.sendLine(1, "CAP REQ :userhost-in-names")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("userhost-in-names ?")],
            fail_msg="Expected CAP ACK after sending CAP REQ, got {msg}.",
        )

        self.sendLine(1, "CAP LIST")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[
                ANYSTR,
                "LIST",
                StrRe(
                    "(multi-prefix userhost-in-names|userhost-in-names multi-prefix) ?"
                ),
            ],
            fail_msg="Expected CAP LIST after sending CAP LIST, got {msg}.",
        )

        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
        )

    @cases.mark_specifications("IRCv3")
    @cases.xfailIfSoftware(
        ["ngIRCd"],
        "does not support userhost-in-names",
    )
    def testReqPostRegistration(self):
        """Tests requesting more capabilities after CAP END"""
        self.addClient(1)
        self.sendLine(1, "CAP LS")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")

        self.sendLine(1, "CAP REQ :multi-prefix")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("multi-prefix ?")],
            fail_msg="Expected CAP ACK after sending CAP REQ, got {msg}.",
        )

        self.sendLine(1, "CAP LIST")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "LIST", StrRe("multi-prefix ?")],
            fail_msg="Expected CAP LIST after sending CAP LIST, got {msg}.",
        )

        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
        )

        self.getMessages(1)

        self.sendLine(1, "CAP REQ :userhost-in-names")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("userhost-in-names ?")],
            fail_msg="Expected CAP ACK after sending CAP REQ, got {msg}.",
        )

        self.sendLine(1, "CAP LIST")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[
                ANYSTR,
                "LIST",
                StrRe(
                    "(multi-prefix userhost-in-names|userhost-in-names multi-prefix) ?"
                ),
            ],
            fail_msg="Expected CAP LIST after sending CAP LIST, got {msg}.",
        )

    @cases.mark_specifications("IRCv3")
    def testReqUnavailable(self):
        """Test the server handles gracefully clients which request
        capabilities that are not available.
        <http://ircv3.net/specs/core/capability-negotiation-3.1.html>
        """
        self.addClient(1)
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "CAP REQ :foo")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "NAK", StrRe("foo ?")],
            fail_msg="Expected CAP NAK after requesting non-existing "
            "capability, got {msg}.",
        )
        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
        )

    @cases.mark_specifications("IRCv3")
    def testNakExactString(self):
        """“The argument of the NAK subcommand MUST consist of at least the
        first 100 characters of the capability list in the REQ subcommand which
        triggered the NAK.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-nak-subcommand>
        """  # noqa
        self.addClient(1)
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)
        # Five should be enough to check there is no reordering, even
        # alphabetical
        self.sendLine(1, "CAP REQ :foo qux bar baz qux quux")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "NAK", "foo qux bar baz qux quux"],
            fail_msg="Expected “CAP NAK :foo qux bar baz qux quux” after "
            "sending “CAP REQ :foo qux bar baz qux quux”, but got {msg}.",
        )

    @cases.mark_specifications("IRCv3")
    def testNakWhole(self):
        """“The capability identifier set must be accepted as a whole, or
        rejected entirely.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-req-subcommand>
        """  # noqa
        self.addClient(1)
        self.sendLine(1, "CAP LS 302")
        if "multi-prefix" not in self.getCapLs(1):
            raise CapabilityNotSupported("multi-prefix")
        self.sendLine(1, "CAP REQ :foo multi-prefix bar")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "NAK", "foo multi-prefix bar"],
            fail_msg="Expected “CAP NAK :foo multi-prefix bar” after "
            "sending “CAP REQ :foo multi-prefix bar”, but got {msg}.",
        )
        self.sendLine(1, "CAP REQ :multi-prefix bar")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "NAK", "multi-prefix bar"],
            fail_msg="Expected “CAP NAK :multi-prefix bar” after "
            "sending “CAP REQ :multi-prefix bar”, but got {msg}.",
        )
        self.sendLine(1, "CAP REQ :foo multi-prefix")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "NAK", "foo multi-prefix"],
            fail_msg="Expected “CAP NAK :foo multi-prefix” after "
            "sending “CAP REQ :foo multi-prefix”, but got {msg}.",
        )
        # TODO: make sure multi-prefix is not enabled at this point
        self.sendLine(1, "CAP REQ :multi-prefix")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=[ANYSTR, "ACK", StrRe("multi-prefix ?")],
            fail_msg="Expected “CAP ACK :multi-prefix” after "
            "sending “CAP REQ :multi-prefix”, but got {msg}.",
        )

    @cases.mark_specifications("IRCv3")
    def testCapRemovalByClient(self):
        """Test CAP LIST and removal of caps via CAP REQ :-tagname."""
        cap1 = "echo-message"
        cap2 = "server-time"
        self.addClient(1)
        self.connectClient("sender")
        self.sendLine(1, "CAP LS 302")
        caps = set()
        while True:
            m = self.getRegistrationMessage(1)
            caps.update(m.params[-1].split())
            if m.params[2] != "*":
                break
        if not ({cap1, cap2} <= caps):
            raise CapabilityNotSupported(f"{cap1} or {cap2}")
        self.sendLine(1, f"CAP REQ :{cap1} {cap2}")
        self.sendLine(1, "nick bar")
        self.sendLine(1, "user user 0 * realname")
        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(m, command="CAP", params=[ANYSTR, "ACK", ANYSTR])
        self.assertEqual(
            set(m.params[2].split()), {cap1, cap2}, "Didn't ACK both REQed caps"
        )
        self.skipToWelcome(1)

        self.sendLine(1, "CAP LIST")
        messages = self.getMessages(1)
        cap_list = [m for m in messages if m.command == "CAP"][0]
        enabled_caps = set(cap_list.params[2].split())
        enabled_caps.discard("cap-notify")  # implicitly added by some impls
        self.assertEqual(enabled_caps, {cap1, cap2})

        self.sendLine(2, "PRIVMSG bar :hi")
        self.getMessages(2)  # Synchronize

        m = self.getMessage(1)
        self.assertIn("time", m.tags, m)

        # remove the multi-prefix cap
        self.sendLine(1, f"CAP REQ :-{cap2}")
        m = self.getMessage(1)
        # Must be either ACK or NAK
        if self.messageDiffers(
            m, command="CAP", params=[ANYSTR, "ACK", StrRe(f"-{cap2} ?")]
        ):
            self.assertMessageMatch(
                m, command="CAP", params=[ANYSTR, "NAK", StrRe(f"-{cap2} ?")]
            )
            raise OptionalBehaviorNotSupported(OptionalBehaviors.CAP_REQ_MINUS)

        # multi-prefix should be disabled
        self.sendLine(1, "CAP LIST")
        messages = self.getMessages(1)
        cap_list = [m for m in messages if m.command == "CAP"][0]
        enabled_caps = set(cap_list.params[2].split())
        enabled_caps.discard("cap-notify")  # implicitly added by some impls
        self.assertEqual(enabled_caps, {cap1})
        self.assertNotIn("time", cap_list.tags)

    @cases.mark_specifications("IRCv3")
    def testIrc301CapLs(self):
        """
        Current version:

        "The LS subcommand is used to list the capabilities supported by the server.
        The client should send an LS subcommand with no other arguments to solicit
        a list of all capabilities."

        "If a client has not indicated support for CAP LS 302 features,
        the server MUST NOT send these new features to the client."
        -- <https://ircv3.net/specs/core/capability-negotiation.html>

        Before the v3.1 / v3.2 merge:

        IRCv3.1: “The LS subcommand is used to list the capabilities
        supported by the server. The client should send an LS subcommand with
        no other arguments to solicit a list of all capabilities.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-ls-subcommand>

        IRCv3.2: “Servers MUST NOT send messages described by this document if
        the client only supports version 3.1.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.2.html#version-in-cap-ls>
        """  # noqa
        self.addClient()
        self.sendLine(1, "CAP LS")
        m = self.getRegistrationMessage(1)
        self.assertNotEqual(
            m.params[2],
            "*",
            m,
            fail_msg="Server replied with multi-line CAP LS to a "
            "“CAP LS” (ie. IRCv3.1) request: {msg}",
        )
        self.assertFalse(
            any("=" in cap for cap in m.params[2].split()),
            "Server replied with a name-value capability in "
            "CAP LS reply as a response to “CAP LS” (ie. IRCv3.1) "
            "request: {}".format(m),
        )

    @cases.mark_specifications("IRCv3")
    def testEmptyCapList(self):
        """“If no capabilities are active, an empty parameter must be sent.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-list-subcommand>
        """  # noqa
        self.addClient()
        self.sendLine(1, "CAP LIST")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m,
            command="CAP",
            params=["*", "LIST", ""],
            fail_msg="Sending “CAP LIST” as first message got a reply "
            "that is not “CAP * LIST :”: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    def testNoMultiline301Response(self):
        """
        Current version: "If the client supports CAP version 302, the server MAY send
        multiple lines in response to CAP LS and CAP LIST." This should be read as
        disallowing multiline responses to pre-302 clients.
        -- <https://ircv3.net/specs/extensions/capability-negotiation#multiline-replies-to-cap-ls-and-cap-list>
        """  # noqa
        self.check301ResponsePreRegistration("bar", "CAP LS")
        self.check301ResponsePreRegistration("qux", "CAP LS 301")
        self.check301ResponsePostRegistration("baz", "CAP LS")
        self.check301ResponsePostRegistration("bat", "CAP LS 301")

    def check301ResponsePreRegistration(self, nick, cap_ls):
        self.addClient(nick)
        self.sendLine(nick, cap_ls)
        self.sendLine(nick, "NICK " + nick)
        self.sendLine(nick, "USER u s e r")
        self.sendLine(nick, "CAP END")
        responses = [msg for msg in self.skipToWelcome(nick) if msg.command == "CAP"]
        self.assertLessEqual(len(responses), 1, responses)

    def check301ResponsePostRegistration(self, nick, cap_ls):
        self.connectClient(nick, name=nick)
        self.sendLine(nick, cap_ls)
        responses = [msg for msg in self.getMessages(nick) if msg.command == "CAP"]
        self.assertLessEqual(len(responses), 1, responses)
