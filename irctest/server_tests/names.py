from irctest import cases
from irctest.numerics import RPL_ENDOFNAMES, RPL_NAMREPLY
from irctest.patma import ANYSTR


class NamesTestCase(cases.BaseServerTestCase):
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

    @cases.mark_specifications("RFC2812")
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

    @cases.mark_specifications("RFC2812")
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
