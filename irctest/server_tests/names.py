"""
The NAMES command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5>`__,
`Modern <https://modern.ircdocs.horse/#names-message>`__)
"""

from irctest import cases, runner
from irctest.numerics import RPL_ENDOFNAMES, RPL_NAMREPLY
from irctest.patma import ANYSTR, StrRe


class NamesTestCase(cases.BaseServerTestCase):
    def _testNames(self, symbol):
        self.connectClient("nick1")
        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)
        self.connectClient("nick2")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, "NAMES #chan")

        # TODO: It is technically allowed to have one line for each;
        # but noone does that.
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_NAMREPLY,
            params=[
                "nick1",
                *(["="] if symbol else []),
                "#chan",
                StrRe("(nick2 @nick1|@nick1 nick2)"),
            ],
        )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFNAMES,
            params=["nick1", "#chan", ANYSTR],
        )

    @cases.mark_specifications("RFC1459", deprecated=True)
    def testNames1459(self):
        """
        https://modern.ircdocs.horse/#names-message
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNames(symbol=False)

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testNames2812(self):
        """
        https://modern.ircdocs.horse/#names-message
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNames(symbol=True)

    @cases.mark_specifications("RFC2812", "Modern")
    def testNames2812Secret(self):
        """The symbol sent for a secret channel is `@` instead of `=`:
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        https://modern.ircdocs.horse/#rplnamreply-353
        """
        self.connectClient("nick1")
        self.sendLine(1, "JOIN #chan")
        # enable secret channel mode
        self.sendLine(1, "MODE #chan +s")
        self.getMessages(1)
        self.sendLine(1, "NAMES #chan")
        messages = self.getMessages(1)
        self.assertMessageMatch(
            messages[0],
            command=RPL_NAMREPLY,
            params=["nick1", "@", "#chan", StrRe("@nick1 ?")],
        )
        self.assertMessageMatch(
            messages[1],
            command=RPL_ENDOFNAMES,
            params=["nick1", "#chan", ANYSTR],
        )

        self.connectClient("nick2")
        self.sendLine(2, "JOIN #chan")
        namreplies = [msg for msg in self.getMessages(2) if msg.command == RPL_NAMREPLY]
        self.assertNotEqual(len(namreplies), 0)
        for msg in namreplies:
            self.assertMessageMatch(
                msg, command=RPL_NAMREPLY, params=["nick2", "@", "#chan", ANYSTR]
            )

    def _testNamesMultipleChannels(self, symbol):
        self.connectClient("nick1")

        if self.targmax.get("NAMES", "1") == "1":
            raise runner.OptionalExtensionNotSupported("Multi-target NAMES")

        self.sendLine(1, "JOIN #chan1")
        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self.sendLine(1, "NAMES #chan1,#chan2")

        # TODO: order is unspecified
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_NAMREPLY,
            params=["nick1", *(["="] if symbol else []), "#chan1", "@nick1"],
        )
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_NAMREPLY,
            params=["nick1", *(["="] if symbol else []), "#chan2", "@nick1"],
        )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFNAMES,
            params=["nick1", "#chan1,#chan2", ANYSTR],
        )

    @cases.mark_isupport("TARGMAX")
    @cases.mark_specifications("RFC1459", deprecated=True)
    def testNamesMultipleChannels1459(self):
        """
        https://modern.ircdocs.horse/#names-message
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNamesMultipleChannels(symbol=False)

    @cases.mark_isupport("TARGMAX")
    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testNamesMultipleChannels2812(self):
        """
        https://modern.ircdocs.horse/#names-message
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNamesMultipleChannels(symbol=True)

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testNamesInvalidChannel(self):
        """
        "There is no error reply for bad channel names."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5

        "If the channel name is invalid or the channel does not exist,
        one `RPL_ENDOFNAMES` numeric containing the given channel name
        should be returned."
        -- https://modern.ircdocs.horse/#names-message
        """
        self.connectClient("foo")
        self.getMessages(1)

        self.sendLine(1, "NAMES invalid")
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFNAMES,
            params=["foo", "invalid", ANYSTR],
        )

    @cases.mark_specifications("RFC1459", "RFC2812", "Modern")
    def testNamesNonexistingChannel(self):
        """
        "There is no error reply for bad channel names."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5

        "If the channel name is invalid or the channel does not exist,
        one `RPL_ENDOFNAMES` numeric containing the given channel name
        should be returned."
        -- https://modern.ircdocs.horse/#names-message
        """
        self.connectClient("foo")
        self.getMessages(1)

        self.sendLine(1, "NAMES #nonexisting")
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFNAMES,
            params=["foo", "#nonexisting", ANYSTR],
        )

    def _testNamesNoArgumentPublic(self, symbol):
        self.connectClient("nick1")
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan1")
        self.connectClient("nick2")
        self.sendLine(2, "JOIN #chan2")
        self.sendLine(2, "MODE #chan2 -sp")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "NAMES")

        # TODO: order is unspecified
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_NAMREPLY,
            params=["nick1", *(["="] if symbol else []), "#chan1", "@nick1"],
        )
        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_NAMREPLY,
            params=["nick1", *(["="] if symbol else []), "#chan2", "@nick2"],
        )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFNAMES,
            params=["nick1", ANYSTR, ANYSTR],
        )

    @cases.mark_specifications("RFC1459", deprecated=True)
    def testNamesNoArgumentPublic1459(self):
        """
        "If no <channel> parameter is given, a list of all channels and their
        occupants is returned."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNamesNoArgumentPublic(symbol=False)

    @cases.mark_specifications("RFC2812", deprecated=True)
    def testNamesNoArgumentPublic2812(self):
        """
        "If no <channel> parameter is given, a list of all channels and their
        occupants is returned."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNamesNoArgumentPublic(symbol=True)

    def _testNamesNoArgumentPrivate(self, symbol):
        self.connectClient("nick1")
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan1")
        self.connectClient("nick2")
        self.sendLine(2, "JOIN #chan2")
        self.sendLine(2, "MODE #chan2 +sp")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "NAMES")

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_NAMREPLY,
            params=["nick1", *(["="] if symbol else []), "#chan1", "@nick1"],
        )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFNAMES,
            params=["nick1", ANYSTR, ANYSTR],
        )

    @cases.mark_specifications("RFC1459", deprecated=True)
    def testNamesNoArgumentPrivate1459(self):
        """
        "If no <channel> parameter is given, a list of all channels and their
        occupants is returned.  At the end of this list, a list of users who
        are visible but either not on any channel or not on a visible channel
        are listed as being on `channel' "*"."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNamesNoArgumentPrivate(symbol=False)

    @cases.mark_specifications("RFC2812", deprecated=True)
    def testNamesNoArgumentPrivate2812(self):
        """
        "If no <channel> parameter is given, a list of all channels and their
        occupants is returned.  At the end of this list, a list of users who
        are visible but either not on any channel or not on a visible channel
        are listed as being on `channel' "*"."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.5
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.5
        """
        self._testNamesNoArgumentPrivate(symbol=True)
