from irctest import cases
from irctest.numerics import ERR_NEEDMOREPARAMS, ERR_NOORIGIN
from irctest.patma import ANYSTR


class PingPongTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testPing(self):
        """https://github.com/ircdocs/modern-irc/pull/99"""
        self.connectClient("foo")
        self.sendLine(1, "PING abcdef")
        self.assertMessageMatch(
            self.getMessage(1), command="PONG", params=["My.Little.Server", "abcdef"]
        )

    @cases.mark_specifications("Modern")
    def testPingNoToken(self):
        """https://github.com/ircdocs/modern-irc/pull/99"""
        self.connectClient("foo")
        self.sendLine(1, "PING")
        m = self.getMessage(1)
        if m.command == ERR_NOORIGIN:
            self.assertMessageMatch(m, command=ERR_NOORIGIN, params=["foo", ANYSTR])
        else:
            self.assertMessageMatch(
                m, command=ERR_NEEDMOREPARAMS, params=["foo", "PING", ANYSTR]
            )

    @cases.mark_specifications("Modern")
    def testPingEmptyToken(self):
        """https://github.com/ircdocs/modern-irc/pull/99"""
        self.connectClient("foo")
        self.sendLine(1, "PING :")
        m = self.getMessage(1)
        if m.command == "PONG":
            self.assertMessageMatch(m, command="PONG", params=["My.Little.Server", ""])
        elif m.command == ERR_NOORIGIN:
            self.assertMessageMatch(m, command=ERR_NOORIGIN, params=["foo", ANYSTR])
        else:
            self.assertMessageMatch(
                m, command=ERR_NEEDMOREPARAMS, params=["foo", "PING", ANYSTR]
            )
