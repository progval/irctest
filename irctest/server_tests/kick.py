"""
The KICK command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.>`__,
`Modern <https://modern.ircdocs.horse/#kick-message>`__)
"""

import pytest

from irctest import cases, client_mock, runner
from irctest.numerics import (
    ERR_CHANOPRIVSNEEDED,
    ERR_NOSUCHCHANNEL,
    ERR_NOTONCHANNEL,
    RPL_NAMREPLY,
)
from irctest.patma import ANYSTR


class KickTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testKickSendsMessages(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes […] KICK”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.1>

        "If a comment is given, this will be sent instead of the default message,
        the nickname of the user targeted by the KICK."
        -- https://modern.ircdocs.horse/#kick-message
        """
        self.connectClient("foo")
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.joinChannel(2, "#chan")

        self.connectClient("baz")
        self.joinChannel(3, "#chan")

        # TODO: check foo is an operator

        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)
        self.sendLine(1, "KICK #chan bar :bye")
        try:
            m = self.getMessage(1)
            if m.command == "482":
                raise runner.ImplementationChoice(
                    "Channel creators are not opped by default."
                )
            self.assertMessageMatch(m, command="KICK")
        except client_mock.NoMessageException:
            # The RFCs do not say KICK must be echoed
            pass
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="KICK", params=["#chan", "bar", "bye"])
        m = self.getMessage(3)
        self.assertMessageMatch(m, command="KICK", params=["#chan", "bar", "bye"])

    def _testKickNoComment(self, check_default):
        self.connectClient("foo")
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.joinChannel(2, "#chan")

        self.connectClient("baz")
        self.joinChannel(3, "#chan")

        # TODO: check foo is an operator

        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)
        self.sendLine(1, "KICK #chan bar")
        try:
            m = self.getMessage(1)
            if m.command == "482":
                raise runner.ImplementationChoice(
                    "Channel creators are not opped by default."
                )
            self.assertMessageMatch(m, command="KICK")
        except client_mock.NoMessageException:
            # The RFCs do not say KICK must be echoed
            pass
        m2 = self.getMessage(2)
        m3 = self.getMessage(3)
        if check_default:
            self.assertMessageMatch(m2, command="KICK", params=["#chan", "bar", "foo"])
            self.assertMessageMatch(m3, command="KICK", params=["#chan", "bar", "foo"])
        else:
            self.assertMessageMatch(m2, command="KICK", params=["#chan", "bar", ANYSTR])
            self.assertMessageMatch(m3, command="KICK", params=["#chan", "bar", ANYSTR])

    @cases.mark_specifications("RFC2812")
    @cases.xfailIfSoftware(
        ["Charybdis", "ircu2", "irc2", "Solanum"],
        "uses the nick of the kickee rather than the kicker.",
    )
    def testKickDefaultComment(self):
        """
        "If a "comment" is
        given, this will be sent instead of the default message, the nickname
        of the user issuing the KICK."
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.8
        """
        self._testKickNoComment(check_default=True)

    @cases.mark_specifications("Modern")
    def testKickNoComment(self):
        """
        "If no comment is given, the server SHOULD use a default message instead."
        -- https://modern.ircdocs.horse/#kick-message
        """
        self._testKickNoComment(check_default=False)

    @cases.mark_specifications("RFC2812")
    def testKickPrivileges(self):
        """Test who has the ability to kick / what error codes are sent
        for invalid kicks."""
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)

        self.connectClient("bar")
        self.sendLine(2, "JOIN #chan")

        messages = self.getMessages(2)
        names = set()
        for message in messages:
            if message.command == RPL_NAMREPLY:
                names.update(set(message.params[-1].split()))
        # assert foo is opped
        self.assertIn("@foo", names, f"unexpected names: {names}")

        self.connectClient("baz")

        self.sendLine(3, "KICK #chan bar")
        replies = set(m.command for m in self.getMessages(3))
        self.assertTrue(
            ERR_NOTONCHANNEL in replies
            or ERR_CHANOPRIVSNEEDED in replies
            or ERR_NOSUCHCHANNEL in replies,
            f"did not receive acceptable error code for kick from outside channel: "
            f"{replies}",
        )

        self.joinChannel(3, "#chan")
        self.getMessages(3)
        self.sendLine(3, "KICK #chan bar")
        replies = set(m.command for m in self.getMessages(3))
        # now we're a channel member so we should receive ERR_CHANOPRIVSNEEDED
        self.assertIn(ERR_CHANOPRIVSNEEDED, replies)

        self.sendLine(1, "MODE #chan +o baz")
        self.getMessages(1)
        # should be able to kick an unprivileged user:
        self.sendLine(3, "KICK #chan bar")
        # should be able to kick an operator:
        self.sendLine(3, "KICK #chan foo")
        baz_replies = set(m.command for m in self.getMessages(3))
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, baz_replies)
        kick_targets = [m.params[1] for m in self.getMessages(1) if m.command == "KICK"]
        # foo should see bar and foo being kicked
        self.assertTrue(
            any(target.startswith("foo") for target in kick_targets),
            f"unexpected kick targets: {kick_targets}",
        )
        self.assertTrue(
            any(target.startswith("bar") for target in kick_targets),
            f"unexpected kick targets: {kick_targets}",
        )

    @cases.mark_specifications("RFC2812")
    def testKickNonexistentChannel(self):
        """“Kick command [...] Numeric replies: [...] ERR_NOSUCHCHANNEL."""
        self.connectClient("nick")

        self.connectClient("foo")
        self.sendLine(1, "KICK #chan nick")
        m = self.getMessage(1)
        # should return ERR_NOSUCHCHANNEL
        self.assertMessageMatch(m, command="403")

    @pytest.mark.parametrize("multiple_targets", [True, False])
    @cases.mark_specifications("RFC2812", "Modern", "ircdocs")
    def testDoubleKickMessages(self, multiple_targets):
        """“The server MUST NOT send KICK messages with multiple channels or
        users to clients.  This is necessarily to maintain backward
        compatibility with old client software.”
        -- https://tools.ietf.org/html/rfc2812#section-3.2.8

        "The server MUST NOT send KICK messages with multiple channels or
        users to clients.
        This is necessary to maintain backward compatibility with existing
        client software."
        -- https://modern.ircdocs.horse/#kick-message

        "Servers MAY limit the number of target users per `KICK` command
        via the [`TARGMAX` parameter of `RPL_ISUPPORT`](#targmax-parameter),
        and silently drop targets if the number of targets exceeds the limit."
        -- https://modern.ircdocs.horse/#kick-message

        "If the "TARGMAX" parameter is not advertised or a value is not sent
        then a client SHOULD assume that no commands except the "JOIN" and "PART"
        commands accept multiple parameters."
        -- https://defs.ircdocs.horse/defs/isupport.html#targmax

        "If this parameter is not advertised or a value is not sent then a client
        SHOULD assume that no commands except the `JOIN` and `PART` commands
        accept multiple parameters."
        -- https://github.com/ircdocs/modern-irc/pull/113

        "If <limit> is not specified, then there is no maximum number of targets
        for that command."
        -- https://modern.ircdocs.horse/#targmax-parameter
        """
        self.connectClient("foo")
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.joinChannel(2, "#chan")

        self.connectClient("baz")
        self.joinChannel(3, "#chan")

        self.connectClient("qux")
        self.joinChannel(4, "#chan")

        targmax = dict(
            item.split(":", 1)
            for item in self.server_support.get("TARGMAX", "").split(",")
            if item
        )
        if targmax.get("KICK", "1") == "1":
            raise runner.OptionalExtensionNotSupported("Multi-target KICK")

        # TODO: check foo is an operator

        # Synchronize
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)
        self.getMessages(4)

        if multiple_targets:
            self.sendLine(1, "KICK #chan,#chan bar,baz :bye")
        else:
            self.sendLine(1, "KICK #chan bar,baz :bye")
        try:
            m = self.getMessage(1)
            if m.command == "482":
                raise runner.OptionalExtensionNotSupported(
                    "Channel creators are not opped by default."
                )
        except client_mock.NoMessageException:
            # The RFCs do not say KICK must be echoed
            pass

        mgroup = self.getMessages(4)
        self.assertGreaterEqual(len(mgroup), 2, mgroup)
        m1, m2 = mgroup[:2]

        self.assertMessageMatch(m1, command="KICK", params=["#chan", ANYSTR, "bye"])
        self.assertMessageMatch(m2, command="KICK", params=["#chan", ANYSTR, "bye"])

        if (m1.params[1] == "bar" and m2.params[1] == "baz") or (
            m1.params[1] == "baz" and m2.params[1] == "bar"
        ):
            ...  # success
        else:
            raise AssertionError(
                "Middle params [{}, {}] are not correct.".format(
                    m1.params[1], m2.params[1]
                )
            )
