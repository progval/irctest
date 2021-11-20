"""
The INFO command.
"""

import pytest

from irctest import cases
from irctest.numerics import ERR_NOSUCHSERVER, RPL_ENDOFINFO, RPL_INFO
from irctest.patma import ANYSTR


class InfoTestCase(cases.BaseServerTestCase):
    @pytest.mark.parametrize(
        "target",
        [None, "My.Little.Server", "*Little*", "nick"],
        ids=["without-target", "target-server", "target-wildcard", "target-nick"],
    )
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testInfo(self, target):
        """
        <https://datatracker.ietf.org/doc/html/rfc1459#section-4.3.8>
        <https://datatracker.ietf.org/doc/html/rfc2812#section-3.4.10>

        "Upon receiving an INFO command, the given server will respond with zero or
        more RPL_INFO replies, followed by one RPL_ENDOFINFO numeric"
        -- <https://modern.ircdocs.horse/#info-message>
        """
        self.connectClient("nick")

        if target:
            self.sendLine(1, "INFO My.Little.Server")
        else:
            self.sendLine(1, "INFO")

        messages = self.getMessages(1)
        last_message = messages.pop()

        self.assertMessageMatch(
            last_message, command=RPL_ENDOFINFO, params=["nick", ANYSTR]
        )

        for message in messages:
            self.assertMessageMatch(message, command=RPL_INFO, params=["nick", ANYSTR])

    @pytest.mark.parametrize("target", ["invalid.server.example", "invalidserver"])
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testInfoNosuchserver(self, target):
        """
        <https://datatracker.ietf.org/doc/html/rfc1459#section-4.3.8>
        <https://datatracker.ietf.org/doc/html/rfc2812#section-3.4.10>

        "Upon receiving an INFO command, the given server will respond with zero or
        more RPL_INFO replies, followed by one RPL_ENDOFINFO numeric"
        -- <https://modern.ircdocs.horse/#info-message>
        """
        self.connectClient("nick")

        self.sendLine(1, f"INFO {target}")

        self.assertMessageMatch(
            self.getMessage(1),
            command=ERR_NOSUCHSERVER,
            params=["nick", target, ANYSTR],
        )
