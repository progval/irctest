"""
The QUITcommand  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.1.6>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.1>`__,
`Modern <https://modern.ircdocs.horse/#quit-message>`__)

TODO: cross-reference RFC 1459 and Modern
"""

import time

from irctest import cases
from irctest.patma import StrRe


class ChannelQuitTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812")
    @cases.xfailIfSoftware(["ircu2", "Nefarious", "snircd"], "ircu2 does not echo QUIT")
    def testQuit(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes [...] QUIT”
        <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient("bar")
        self.joinChannel(1, "#chan")
        self.connectClient("qux")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)

        self.getMessages(1)

        # Despite `anti_spam_exit_message_time = 0`, hybrid does not immediately
        # allow custom PART reasons.
        time.sleep(1)

        self.sendLine(2, "QUIT :qux out")
        self.getMessages(2)
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="QUIT", params=[StrRe(".*qux out.*")])
        self.assertTrue(m.prefix.startswith("qux"))  # nickmask of quitter
