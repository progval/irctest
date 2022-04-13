"""
The LIST command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.6>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.6>`__,
`Modern <https://modern.ircdocs.horse/#list-message>`__)
"""

import time

from irctest import cases, runner
from irctest.numerics import RPL_LIST, RPL_LISTEND, RPL_LISTSTART


class _BasedListTestCase(cases.BaseServerTestCase):
    def _parseChanList(self, client):
        channels = set()
        while True:
            m = self.getMessage(client)
            if m.command == RPL_LISTEND:
                break
            if m.command == RPL_LIST:
                if m.params[1].startswith("&"):
                    # skip local pseudo-channels listed by ngircd and ircu
                    continue
                channels.add(m.params[1])

        return channels


class ListTestCase(_BasedListTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    @cases.xfailIfSoftware(["irc2"], "irc2 deprecated LIST")
    def testListEmpty(self):
        """<https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>
        <https://modern.ircdocs.horse/#list-message>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.sendLine(2, "LIST")
        m = self.getMessage(2)
        if m.command == RPL_LISTSTART:
            # skip
            m = self.getMessage(2)
        # skip local pseudo-channels listed by ngircd and ircu
        while m.command == RPL_LIST and m.params[1].startswith("&"):
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            RPL_LIST,
            "LIST response gives (at least) one channel, whereas there " "is none.",
        )
        self.assertMessageMatch(
            m,
            command=RPL_LISTEND,
            fail_msg="Second reply to LIST is not 322 (RPL_LIST) "
            "or 323 (RPL_LISTEND), or but: {msg}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    @cases.xfailIfSoftware(["irc2"], "irc2 deprecated LIST")
    def testListOne(self):
        """When a channel exists, LIST should get it in a reply.
        <https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>

        <https://modern.ircdocs.horse/#list-message>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)
        self.sendLine(2, "LIST")
        m = self.getMessage(2)
        if m.command == RPL_LISTSTART:
            # skip
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            RPL_LISTEND,
            fail_msg="LIST response ended (ie. 323, aka RPL_LISTEND) "
            "without listing any channel, whereas there is one.",
        )
        self.assertMessageMatch(
            m,
            command=RPL_LIST,
            fail_msg="Second reply to LIST is not 322 (RPL_LIST), "
            "nor 323 (RPL_LISTEND) but: {msg}",
        )
        m = self.getMessage(2)
        # skip local pseudo-channels listed by ngircd and ircu
        while m.command == RPL_LIST and m.params[1].startswith("&"):
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            RPL_LIST,
            fail_msg="LIST response gives (at least) two channels, "
            "whereas there is only one.",
        )
        self.assertMessageMatch(
            m,
            command=RPL_LISTEND,
            fail_msg="Third reply to LIST is not 322 (RPL_LIST) "
            "or 323 (RPL_LISTEND), or but: {msg}",
        )

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    def testListMask(self):
        """
        "M: Searching based on mask."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8
        """
        self.connectClient("foo")

        if "M" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=M")

        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan1")
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self.sendLine(2, "LIST *an1")
        self.assertEqual(self._parseChanList(2), {"#chan1"})

        self.sendLine(2, "LIST *an2")
        self.assertEqual(self._parseChanList(2), {"#chan2"})

        self.sendLine(2, "LIST #c*n2")
        self.assertEqual(self._parseChanList(2), {"#chan2"})

        self.sendLine(2, "LIST *an3")
        self.assertEqual(self._parseChanList(2), set())

        self.sendLine(2, "LIST #ch*")
        self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    def testListNotMask(self):
        """
        " N: Searching based on a non-matching mask. i.e., the opposite of M."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8
        """
        self.connectClient("foo")

        if "N" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=N")

        self.sendLine(1, "JOIN #chan1")
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self.connectClient("bar")

        self.sendLine(2, "LIST !*an1")
        self.assertEqual(self._parseChanList(2), {"#chan2"})

        self.sendLine(2, "LIST !*an2")
        self.assertEqual(self._parseChanList(2), {"#chan1"})

        self.sendLine(2, "LIST !#c*n2")
        self.assertEqual(self._parseChanList(2), {"#chan1"})

        self.sendLine(2, "LIST !*an3")
        self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})

        self.sendLine(2, "LIST !#ch*")
        self.assertEqual(self._parseChanList(2), set())

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    def testListUsers(self):
        """
        "U: Searching based on user count within the channel, via the "<val" and
        ">val" modifiers to search for a channel that has less or more than val users,
        respectively."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8
        """
        self.connectClient("foo")

        if "M" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=M")

        self.sendLine(1, "JOIN #chan1")
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self.connectClient("bar")
        self.sendLine(2, "JOIN #chan2")
        self.getMessages(2)

        self.connectClient("baz")

        self.sendLine(3, "LIST >0")
        self.assertEqual(self._parseChanList(3), {"#chan1", "#chan2"})

        self.sendLine(3, "LIST <1")
        self.assertEqual(self._parseChanList(3), set())

        self.sendLine(3, "LIST <100")
        self.assertEqual(self._parseChanList(3), {"#chan1", "#chan2"})

        self.sendLine(3, "LIST >1")
        self.assertEqual(self._parseChanList(3), {"#chan2"})

        self.sendLine(3, "LIST <2")
        self.assertEqual(self._parseChanList(3), {"#chan1"})

        self.sendLine(3, "LIST <100")
        self.assertEqual(self._parseChanList(3), {"#chan1", "#chan2"})


class FaketimeListTestCase(_BasedListTestCase):
    faketime = "+1y x30"  # for every wall clock second, 1 minute passed for the server

    def _sleep_minutes(self, n):
        for _ in range(n):
            if self.controller.faketime_enabled:
                # From the server's point of view, 1 min will pass
                time.sleep(2)
            else:
                time.sleep(60)

            # reply to pings
            self.getMessages(1)
            self.getMessages(2)

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    @cases.xfailIfSoftware(
        ["Plexus4", "Hybrid"],
        "Hybrid and Plexus4 filter on ELIST=C with the opposite meaning",
    )
    @cases.xfailIf(
        lambda self: bool(
            self.controller.software_name == "UnrealIRCd"
            and self.controller.software_version == 5
        ),
        "UnrealIRCd <6.0.3 filters on ELIST=C with the opposite meaning",
    )
    def testListCreationTime(self):
        """
        " C: Searching based on channel creation time, via the "C<val" and "C>val"
        modifiers to search for a channel creation time that is higher or lower
        than val."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8

        Unfortunately, this is ambiguous, because "val" is a time delta (in minutes),
        not a timestamp.

        On InspIRCd and Charybdis/Solanum, "C<val" is interpreted as "the channel was
        created less than <val> minutes ago

        On UnrealIRCd, Plexus, and Hybrid, it is interpreted as "the channel's creation
        time is a timestamp lower than <val> minutes ago" (ie. the exact opposite)

        "C: Searching based on channel creation time, via the "C<val" and "C>val"
        modifiers to search for a channel that was created either less than `val`
        minutes ago, or more than `val` minutes ago, respectively"
        -- https://github.com/ircdocs/modern-irc/pull/171
        """
        self.connectClient("foo")

        if "C" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=C")

        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan1")
        self.getMessages(1)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self._sleep_minutes(2)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self._sleep_minutes(1)

        if self.controller.software_name in ("UnrealIRCd", "Plexus4", "Hybrid"):
            self.sendLine(2, "LIST C<2")
            self.assertEqual(self._parseChanList(2), {"#chan1"})

            self.sendLine(2, "LIST C>2")
            self.assertEqual(self._parseChanList(2), {"#chan2"})

            self.sendLine(2, "LIST C>0")
            self.assertEqual(self._parseChanList(2), set())

            self.sendLine(2, "LIST C<0")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})

            self.sendLine(2, "LIST C>10")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})
        elif self.controller.software_name in (
            "Solanum",
            "Charybdis",
            "InspIRCd",
            "Nefarious",
        ):
            self.sendLine(2, "LIST C>2")
            self.assertEqual(self._parseChanList(2), {"#chan1"})

            self.sendLine(2, "LIST C<2")
            self.assertEqual(self._parseChanList(2), {"#chan2"})

            self.sendLine(2, "LIST C<0")
            if self.controller.software_name == "InspIRCd":
                self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})
            else:
                self.assertEqual(self._parseChanList(2), set())

            self.sendLine(2, "LIST C>0")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})

            self.sendLine(2, "LIST C<10")
            self.assertEqual(self._parseChanList(2), {"#chan1", "#chan2"})
        else:
            assert False, f"{self.controller.software_name} not supported"

    @cases.mark_isupport("ELIST")
    @cases.mark_specifications("Modern")
    @cases.xfailIf(
        lambda self: bool(
            self.controller.software_name == "UnrealIRCd"
            and self.controller.software_version == 5
        ),
        "UnrealIRCd <6.0.3 advertises ELIST=T but does not implement it",
    )
    def testListTopicTime(self):
        """
        "T: Searching based on topic time, via the "T<val" and "T>val"
        modifiers to search for a topic time that is lower or higher than
        val respectively."
        -- <https://modern.ircdocs.horse/#elist-parameter>
        -- https://datatracker.ietf.org/doc/html/draft-hardy-irc-isupport-00#section-4.8

        See testListCreationTime's docstring for comments on this.

        "T: Searching based on topic set time, via the "T<val" and "T>val" modifiers
        to search for a topic time that was set less than `val` minutes ago, or more
        than `val` minutes ago, respectively."
        -- https://github.com/ircdocs/modern-irc/pull/171
        """
        self.connectClient("foo")

        if "T" not in self.server_support.get("ELIST", ""):
            raise runner.OptionalExtensionNotSupported("ELIST=T")

        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan1")
        self.sendLine(1, "JOIN #chan2")
        self.getMessages(1)

        self.sendLine(1, "TOPIC #chan1 :First channel")
        self.getMessages(1)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self._sleep_minutes(2)

        # Helps debugging
        self.sendLine(1, "TIME")
        self.getMessages(1)

        self.sendLine(1, "TOPIC #chan2 :Second channel")
        self.getMessages(1)

        self._sleep_minutes(1)

        self.sendLine(1, "LIST T>2")
        self.assertEqual(self._parseChanList(1), {"#chan1"})

        self.sendLine(1, "LIST T<2")
        self.assertEqual(self._parseChanList(1), {"#chan2"})

        self.sendLine(1, "LIST T<0")
        if self.controller.software_name == "InspIRCd":
            # Insp internally represents "LIST T>0" like "LIST"
            self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})
        else:
            self.assertEqual(self._parseChanList(1), set())

        self.sendLine(1, "LIST T>0")
        self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})

        self.sendLine(1, "LIST T<10")
        self.assertEqual(self._parseChanList(1), {"#chan1", "#chan2"})
