"""
The PART command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-6.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-5.2>`__,
`Modern <https://modern.ircdocs.horse/#part-message>`__)

TODO: cross-reference Modern
"""

import time

from irctest import cases


class PartTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testPartNotInEmptyChannel(self):
        """“442     ERR_NOTONCHANNEL
            "<channel> :You're not on that channel"

        - Returned by the server whenever a client tries to
          perform a channel effecting command for which the
          client isn't a member.”
          -- <https://tools.ietf.org/html/rfc1459#section-6.1>
          and <https://tools.ietf.org/html/rfc2812#section-5.2>

        According to RFCs, ERR_NOSUCHCHANNEL should only be used for invalid
        channel names:
        “403     ERR_NOSUCHCHANNEL
          "<channel name> :No such channel"

        - Used to indicate the given channel name is invalid.”
        -- <https://tools.ietf.org/html/rfc1459#section-6.1>
        and <https://tools.ietf.org/html/rfc2812#section-5.2>

        However, many implementations use 479 instead, so let's allow it.
        <http://danieloaks.net/irc-defs/defs/ircnumerics.html#403>
        <http://danieloaks.net/irc-defs/defs/ircnumerics.html#479>
        """
        self.connectClient("foo")
        self.sendLine(1, "PART #chan")
        m = self.getMessage(1)
        self.assertIn(
            m.command,
            {"442", "403"},
            m,  # ERR_NOTONCHANNEL, ERR_NOSUCHCHANNEL
            fail_msg="Expected ERR_NOTONCHANNEL (442) or "
            "ERR_NOSUCHCHANNEL (403) after PARTing an empty channel "
            "one is not on, but got: {msg}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testPartNotInNonEmptyChannel(self):
        self.connectClient("foo")
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)  # Synchronize
        self.sendLine(2, "PART #chan")
        m = self.getMessage(2)
        self.assertMessageMatch(
            m,
            command="442",  # ERR_NOTONCHANNEL
            fail_msg="Expected ERR_NOTONCHANNEL (442) "
            "after PARTing a non-empty channel "
            "one is not on, but got: {msg}",
        )
        self.assertEqual(self.getMessages(2), [])

    testPartNotInNonEmptyChannel.__doc__ = testPartNotInEmptyChannel.__doc__

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testBasicPart(self):
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])

        self.connectClient("baz")
        self.sendLine(2, "JOIN #chan")
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])

        # skip the rest of the JOIN burst:
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "PART #chan")
        # both the PART'ing client and the other channel member should receive
        # a PART line:
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="PART")
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="PART")

    @cases.mark_specifications("RFC2812")
    def testBasicPartRfc2812(self):
        """
        “If a "Part Message" is given, this will be sent
        instead of the default message, the nickname.”
        """
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])

        self.connectClient("baz")
        self.sendLine(2, "JOIN #chan")
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])

        # skip the rest of the JOIN burst:
        self.getMessages(1)
        self.getMessages(2)

        # Despite `anti_spam_exit_message_time = 0`, hybrid does not immediately
        # allow custom PART reasons.
        time.sleep(1)

        self.sendLine(1, "PART #chan :bye everyone")
        # both the PART'ing client and the other channel member should receive
        # a PART line:
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="PART", params=["#chan", "bye everyone"])
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="PART", params=["#chan", "bye everyone"])

    @cases.mark_specifications("RFC2812")
    def testPartMessage(self):
        """
        “If a "Part Message" is given, this will be sent
        instead of the default message, the nickname.”
        """
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])

        self.connectClient("baz")
        self.sendLine(2, "JOIN #chan")
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])

        # skip the rest of the JOIN burst:
        self.getMessages(1)
        self.getMessages(2)

        # Despite `anti_spam_exit_message_time = 0`, hybrid does not immediately
        # allow custom PART reasons.
        time.sleep(1)

        self.sendLine(1, "PART #chan :bye everyone")
        # both the PART'ing client and the other channel member should receive
        # a PART line:
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="PART", params=["#chan", "bye everyone"])
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="PART", params=["#chan", "bye everyone"])
