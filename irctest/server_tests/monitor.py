"""
`IRCv3 MONITOR <https://ircv3.net/specs/extensions/monitor>`_
"""

from irctest import cases, runner
from irctest.client_mock import NoMessageException
from irctest.numerics import (
    RPL_ENDOFMONLIST,
    RPL_MONLIST,
    RPL_MONOFFLINE,
    RPL_MONONLINE,
)
from irctest.patma import ANYSTR, StrRe


class MonitorTestCase(cases.BaseServerTestCase):
    def check_server_support(self):
        if "MONITOR" not in self.server_support:
            raise runner.IsupportTokenNotSupported("MONITOR")

    def assertMononline(self, client, nick, m=None):
        if not m:
            m = self.getMessage(client)
        self.assertMessageMatch(
            m,
            command="730",  # RPL_MONONLINE
            params=[ANYSTR, StrRe(nick + "(!.*)?")],
            fail_msg="Unexpected notification that monitored nick “{}” "
            "is online: {msg}",
            extra_format=(nick,),
        )

    def assertMonoffline(self, client, nick, m=None):
        if not m:
            m = self.getMessage(client)
        self.assertMessageMatch(
            m,
            command="731",  # RPL_MONOFFLINE
            params=[ANYSTR, nick],
            fail_msg="Unexpected notification that monitored nick “{}” "
            "is offline: {msg}",
            extra_format=(nick,),
        )

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorOneDisconnected(self):
        """“If any of the targets being added are online, the server will
        generate RPL_MONONLINE numerics listing those targets that are
        online.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor--targettarget2>
        """
        self.connectClient("foo")
        self.check_server_support()
        self.sendLine(1, "MONITOR + bar")
        self.assertMonoffline(1, "bar")
        self.connectClient("bar")
        self.assertMononline(1, "bar")
        self.sendLine(2, "QUIT :bye")
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertMonoffline(1, "bar")

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorOneConnection(self):
        self.connectClient("foo")
        self.check_server_support()
        self.sendLine(1, "MONITOR + bar")
        self.getMessages(1)
        self.connectClient("bar")
        self.assertMononline(1, "bar")

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorOneConnected(self):
        """“If any of the targets being added are offline, the server will
        generate RPL_MONOFFLINE numerics listing those targets that are
        online.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor--targettarget2>
        """
        self.connectClient("foo")
        self.check_server_support()
        self.connectClient("bar")
        self.sendLine(1, "MONITOR + bar")
        self.assertMononline(1, "bar")
        self.sendLine(2, "QUIT :bye")
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertMonoffline(1, "bar")

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorOneConnectionWithQuit(self):
        self.connectClient("foo")
        self.check_server_support()
        self.connectClient("bar")
        self.sendLine(1, "MONITOR + bar")
        self.assertMononline(1, "bar")
        self.sendLine(2, "QUIT :bye")
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertMonoffline(1, "bar")
        self.connectClient("bar")
        self.assertMononline(1, "bar")

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorConnectedAndDisconnected(self):
        """“If any of the targets being added are online, the server will
        generate RPL_MONONLINE numerics listing those targets that are
        online.

        If any of the targets being added are offline, the server will
        generate RPL_MONOFFLINE numerics listing those targets that are
        online.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor--targettarget2>
        """
        self.connectClient("foo")
        self.check_server_support()
        self.connectClient("bar")
        self.sendLine(1, "MONITOR + bar,baz")
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)
        commands = {m1.command, m2.command}
        self.assertEqual(
            commands,
            {"730", "731"},
            fail_msg="Did not send one 730 (RPL_MONONLINE) and one "
            "731 (RPL_MONOFFLINE) after “MONITOR + bar,baz” when “bar” "
            "is online and “baz” is offline. Sent this instead: {}",
            extra_format=((m1, m2)),
        )
        if m1.command == "731":
            (m1, m2) = (m2, m1)

        self.assertMononline(None, "bar", m=m1)
        self.assertMonoffline(None, "baz", m=m2)

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testUnmonitor(self):
        self.connectClient("foo")
        self.check_server_support()
        self.sendLine(1, "MONITOR + bar")
        self.getMessages(1)
        self.connectClient("bar")
        self.assertMononline(1, "bar")
        self.sendLine(1, "MONITOR - bar")
        self.assertEqual(
            self.getMessages(1),
            [],
            fail_msg="Got messages after “MONITOR - bar”: {got}",
        )
        self.sendLine(2, "QUIT :bye")
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertEqual(
            self.getMessages(1),
            [],
            fail_msg="Got messages after disconnection of unmonitored " "nick: {got}",
        )

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorForbidsMasks(self):
        """“The MONITOR implementation also enhances user privacy by
        disallowing subscription to hostmasks, allowing users to avoid
        nick-change stalking.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#watch-vs-monitor>

        “For this specification, ‘target’ MUST be a valid nick as determined
        by the IRC daemon.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor-command>
        """
        self.connectClient("foo")
        self.check_server_support()
        self.sendLine(1, "MONITOR + *!username@localhost")
        self.sendLine(1, "MONITOR + *!username@127.0.0.1")
        try:
            m = self.getMessage(1)
            self.assertMessageMatch(m, command="731")
        except NoMessageException:
            pass
        else:
            m = self.getMessage(1)
            self.assertMessageMatch(m, command="731")
        self.connectClient("bar")
        try:
            m = self.getMessage(1)
        except NoMessageException:
            pass
        else:
            raise AssertionError(
                "Got message after client whose MONITORing "
                "was requested via hostmask connected: {}".format(m)
            )

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testTwoMonitoringOneRemove(self):
        """Tests the following scenario:
        * foo MONITORs qux
        * bar MONITORs qux
        * bar unMONITORs qux
        * qux connects.
        """
        self.connectClient("foo")
        self.check_server_support()
        self.connectClient("bar")
        self.sendLine(1, "MONITOR + qux")
        self.sendLine(2, "MONITOR + qux")
        self.getMessages(1)
        self.getMessages(2)
        self.sendLine(2, "MONITOR - qux")
        messages = self.getMessages(2)
        self.assertEqual(
            messages,
            [],
            fail_msg="Got response to “MONITOR -”: {}",
            extra_format=(messages,),
        )
        self.connectClient("qux")
        self.getMessages(3)
        messages = self.getMessages(1)
        self.assertNotEqual(
            messages,
            [],
            fail_msg="Received no message after MONITORed client " "connects.",
        )
        messages = self.getMessages(2)
        self.assertEqual(
            messages,
            [],
            fail_msg="Got response to unmonitored client: {}",
            extra_format=(messages,),
        )

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testMonitorList(self):
        def checkMonitorSubjects(messages, client_nick, expected_targets):
            # collect all the RPL_MONLIST nicks into a set:
            result = set()
            for message in messages:
                if message.command == RPL_MONLIST:
                    self.assertEqual(message.params[0], client_nick)
                    result.update(message.params[1].split(","))
            # finally, RPL_ENDOFMONLIST should be sent
            self.assertEqual(messages[-1].command, RPL_ENDOFMONLIST)
            self.assertEqual(messages[-1].params[0], client_nick)
            self.assertEqual(result, expected_targets)

        self.connectClient("bar")
        self.check_server_support()
        self.sendLine(1, "MONITOR L")
        checkMonitorSubjects(self.getMessages(1), "bar", set())

        self.sendLine(1, "MONITOR + qux")
        self.getMessages(1)
        self.sendLine(1, "MONITOR L")
        checkMonitorSubjects(self.getMessages(1), "bar", {"qux"})

        self.sendLine(1, "MONITOR + bazbat")
        self.getMessages(1)
        self.sendLine(1, "MONITOR L")
        checkMonitorSubjects(self.getMessages(1), "bar", {"qux", "bazbat"})

        self.sendLine(1, "MONITOR - qux")
        self.getMessages(1)
        self.sendLine(1, "MONITOR L")
        checkMonitorSubjects(self.getMessages(1), "bar", {"bazbat"})

    @cases.mark_specifications("IRCv3")
    @cases.mark_isupport("MONITOR")
    def testNickChange(self):
        # see oragono issue #1076: nickname changes must trigger RPL_MONOFFLINE
        self.connectClient("bar")
        self.check_server_support()
        self.sendLine(1, "MONITOR + qux")
        self.getMessages(1)

        self.connectClient("baz")
        self.getMessages(2)
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(2, "NICK qux")
        self.getMessages(2)
        mononline = self.getMessages(1)[0]
        self.assertEqual(mononline.command, RPL_MONONLINE)
        self.assertEqual(len(mononline.params), 2, mononline.params)
        self.assertIn(mononline.params[0], ("bar", "*"))
        self.assertEqual(mononline.params[1].split("!")[0], "qux")

        # no numerics for a case change
        self.sendLine(2, "NICK QUX")
        self.getMessages(2)
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(2, "NICK bazbat")
        self.getMessages(2)
        monoffline = self.getMessages(1)[0]
        # should get RPL_MONOFFLINE with the current unfolded nick
        self.assertEqual(monoffline.command, RPL_MONOFFLINE)
        self.assertEqual(len(monoffline.params), 2, monoffline.params)
        self.assertIn(monoffline.params[0], ("bar", "*"))
        self.assertEqual(monoffline.params[1].split("!")[0], "QUX")
