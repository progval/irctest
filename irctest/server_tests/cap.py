"""
`IRCv3 Capability negotiation
<https://ircv3.net/specs/extensions/capability-negotiation>`_
"""

from irctest import cases
from irctest.patma import ANYSTR
from irctest.runner import CapabilityNotSupported, ImplementationChoice


class CapTestCase(cases.BaseServerTestCase):
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
        self.sendLine(1, "CAP END")
        m = self.getRegistrationMessage(1)
        self.assertMessageMatch(
            m, command="001", fail_msg="Expected 001 after sending CAP END, got {msg}."
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
            params=[ANYSTR, "NAK", "foo"],
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
    @cases.xfailIfSoftware(
        ["UnrealIRCd"],
        "UnrealIRCd sends a trailing space on CAP NAK: https://github.com/unrealircd/unrealircd/pull/148",
    )
    def testNakWhole(self):
        """“The capability identifier set must be accepted as a whole, or
        rejected entirely.”
        -- <http://ircv3.net/specs/core/capability-negotiation-3.1.html#the-cap-req-subcommand>
        """  # noqa
        self.addClient(1)
        self.sendLine(1, "CAP LS 302")
        self.assertIn("multi-prefix", self.getCapLs(1))
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
            params=[ANYSTR, "ACK", "multi-prefix"],
            fail_msg="Expected “CAP ACK :multi-prefix” after "
            "sending “CAP REQ :multi-prefix”, but got {msg}.",
        )

    @cases.mark_specifications("IRCv3")
    @cases.xfailIfSoftware(
        ["UnrealIRCd"],
        "UnrealIRCd sends a trailing space on CAP NAK: https://github.com/unrealircd/unrealircd/pull/148",
    )
    def testCapRemovalByClient(self):
        """Test CAP LIST and removal of caps via CAP REQ :-tagname."""
        cap1 = "echo-message"
        cap2 = "server-time"
        self.addClient(1)
        self.connectClient("sender")
        self.sendLine(1, "CAP LS 302")
        m = self.getRegistrationMessage(1)
        if not ({cap1, cap2} <= set(m.params[2].split())):
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

        # remove the server-time cap
        self.sendLine(1, f"CAP REQ :-{cap2}")
        m = self.getMessage(1)
        # Must be either ACK or NAK
        if self.messageDiffers(m, command="CAP", params=[ANYSTR, "ACK", f"-{cap2}"]):
            self.assertMessageMatch(
                m, command="CAP", params=[ANYSTR, "NAK", f"-{cap2}"]
            )
            raise ImplementationChoice(f"Does not support CAP REQ -{cap2}")

        # server-time should be disabled
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
