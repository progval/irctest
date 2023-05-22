"""
Channel "no external messages" mode (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.3.1>`__,
`Modern <https://modern.ircdocs.horse/#no-external-messages-mode>`__)
"""

from irctest import cases
from irctest.numerics import ERR_CANNOTSENDTOCHAN


class NoOutsideTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459")
    def testNoOutsideMode(self):
        # test the +n channel mode
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.sendLine("chanop", "MODE #chan +n")
        self.getMessages("chanop")

        self.connectClient("baz", name="baz")
        # this message should be suppressed completely by +n
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        replies = self.getMessages("baz")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(ERR_CANNOTSENDTOCHAN, reply_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # set the channel to -n: baz should be able to send now
        self.sendLine("chanop", "MODE #chan -n")
        replies = self.getMessages("chanop")
        modeLines = [line for line in replies if line.command == "MODE"]
        self.assertMessageMatch(modeLines[0], command="MODE", params=["#chan", "-n"])
        self.sendLine("baz", "PRIVMSG #chan :hi again from baz")
        self.getMessages("baz")
        relays = self.getMessages("chanop")
        self.assertMessageMatch(
            relays[0], command="PRIVMSG", params=["#chan", "hi again from baz"]
        )
