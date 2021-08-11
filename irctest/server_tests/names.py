from irctest import cases
from irctest.numerics import RPL_ENDOFNAMES
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
