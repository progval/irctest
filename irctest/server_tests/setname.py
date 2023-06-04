"""
<https://ircv3.net/specs/extensions/setname>`_
"""

from irctest import cases
from irctest.numerics import RPL_WHOISUSER


class SetnameMessageTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("setname")
    def testSetnameMessage(self):
        self.connectClient("foo", capabilities=["setname"], skip_if_cap_nak=True)

        self.sendLine(1, "SETNAME bar")
        self.assertMessageMatch(
            self.getMessage(1),
            command="SETNAME",
            params=["bar"],
        )

        self.sendLine(1, "WHOIS foo")
        whoisuser = [m for m in self.getMessages(1) if m.command == RPL_WHOISUSER][0]
        self.assertEqual(whoisuser.params[-1], "bar")

    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("setname")
    def testSetnameChannel(self):
        """“[Servers] MUST send the server-to-client version of the
        SETNAME message to all clients in common channels, as well as
        to the client from which it originated, to confirm the change
        has occurred.

        The SETNAME message MUST NOT be sent to clients which do not
        have the setname capability negotiated.“
        """
        self.connectClient("foo", capabilities=["setname"], skip_if_cap_nak=True)
        self.connectClient("bar", capabilities=["setname"], skip_if_cap_nak=True)
        self.connectClient("baz")

        self.joinChannel(1, "#chan")
        self.joinChannel(2, "#chan")
        self.joinChannel(3, "#chan")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        self.sendLine(1, "SETNAME qux")
        self.assertMessageMatch(
            self.getMessage(1),
            command="SETNAME",
            params=["qux"],
        )

        self.assertMessageMatch(
            self.getMessage(2),
            command="SETNAME",
            params=["qux"],
        )

        self.assertEqual(
            self.getMessages(3),
            [],
            "Got SETNAME response when it was not negotiated",
        )
