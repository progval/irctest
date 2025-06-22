"""
`IRCv3 MONITOR <https://ircv3.net/specs/extensions/monitor>`_
and `IRCv3 extended-monitor` <https://ircv3.net/specs/extensions/extended-monitor>`_
"""

import pytest

from irctest import cases, runner
from irctest.client_mock import NoMessageException
from irctest.numerics import (
    ERR_ERRONEUSNICKNAME,
    RPL_ENDOFMONLIST,
    RPL_MONLIST,
    RPL_MONOFFLINE,
    RPL_MONONLINE,
)
from irctest.patma import ANYSTR, Either, StrRe


class _BaseMonitorTestCase(cases.BaseServerTestCase):
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


class MonitorTestCase(_BaseMonitorTestCase):
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
        expected_command = Either(RPL_MONOFFLINE, ERR_ERRONEUSNICKNAME)
        try:
            m = self.getMessage(1)
            self.assertMessageMatch(m, command=expected_command)
        except NoMessageException:
            pass
        else:
            m = self.getMessage(1)
            self.assertMessageMatch(m, command=expected_command)
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
    def testMonitorClear(self):
        """“Clears the list of targets being monitored. No output will be returned
        for use of this command.“
        -- <https://ircv3.net/specs/extensions/monitor#monitor-c>
        """
        self.connectClient("foo")
        self.check_server_support()
        self.sendLine(1, "MONITOR + bar")
        self.getMessages(1)

        self.sendLine(1, "MONITOR C")
        self.sendLine(1, "MONITOR L")
        m = self.getMessage(1)
        self.assertEqual(m.command, RPL_ENDOFMONLIST)

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
    def testMonitorStatus(self):
        """“Outputs for each target in the list being monitored, whether
        the client is online or offline. All targets that are online will
        be sent using RPL_MONONLINE, all targets that are offline will be
        sent using RPL_MONOFFLINE.“
        -- <https://ircv3.net/specs/extensions/monitor#monitor-s>
        """
        self.connectClient("foo")
        self.check_server_support()
        self.connectClient("bar")
        self.sendLine(1, "MONITOR + bar,baz")
        self.getMessages(1)

        self.sendLine(1, "MONITOR S")
        msgs = self.getMessages(1)
        self.assertEqual(
            len(msgs),
            2,
            fail_msg="Expected one RPL_MONONLINE (730) and one RPL_MONOFFLINE (731), got: {}",
            extra_format=(msgs,),
        )

        msgs.sort(key=lambda m: m.command)

        self.assertMononline(1, "bar", m=msgs[0])
        self.assertMonoffline(1, "baz", m=msgs[1])

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
        self.assertMessageMatch(
            mononline,
            command=RPL_MONONLINE,
            params=[StrRe(r"(bar|\*)"), StrRe("qux(!.*)?")],
        )

        # no numerics for a case change
        self.sendLine(2, "NICK QUX")
        self.getMessages(2)
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(2, "NICK bazbat")
        self.getMessages(2)
        monoffline = self.getMessages(1)[0]
        # should get RPL_MONOFFLINE with the current unfolded nick
        self.assertMessageMatch(
            monoffline,
            command=RPL_MONOFFLINE,
            params=[StrRe(r"(bar|\*)"), "QUX"],
        )


class _BaseExtendedMonitorTestCase(_BaseMonitorTestCase):
    def _setupExtendedMonitor(self, monitor_before_connect, watcher_caps, watched_caps):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html"""
        self.connectClient(
            "foo",
            capabilities=["extended-monitor", *watcher_caps],
            skip_if_cap_nak=True,
        )

        if monitor_before_connect:
            self.sendLine(1, "MONITOR + bar")
            self.getMessages(1)
            self.connectClient("bar", capabilities=watched_caps, skip_if_cap_nak=True)
            self.getMessages(2)
        else:
            self.connectClient("bar", capabilities=watched_caps, skip_if_cap_nak=True)
            self.getMessages(2)
            self.sendLine(1, "MONITOR + bar")

        self.assertMononline(1, "bar")
        self.assertEqual(self.getMessages(1), [])


class ExtendedMonitorTestCase(_BaseExtendedMonitorTestCase):
    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("extended-monitor", "away-notify")
    @pytest.mark.parametrize(
        "monitor_before_connect,cap",
        [
            pytest.param(
                monitor_before_connect,
                cap,
                id=("monitor_before_connect" if monitor_before_connect else "")
                + "-"
                + ("with-cap" if cap else ""),
            )
            for monitor_before_connect in [True, False]
            for cap in [True, False]
        ],
    )
    def testExtendedMonitorAway(self, monitor_before_connect, cap):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html
        with https://ircv3.net/specs/extensions/away-notify
        """
        if cap:
            self._setupExtendedMonitor(
                monitor_before_connect, ["away-notify"], ["away-notify"]
            )
        else:
            self._setupExtendedMonitor(monitor_before_connect, ["away-notify"], [])

        self.sendLine(2, "AWAY :afk")
        self.getMessages(2)
        self.assertMessageMatch(
            self.getMessage(1), nick="bar", command="AWAY", params=["afk"]
        )
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")

        self.sendLine(2, "AWAY")
        self.getMessages(2)
        self.assertMessageMatch(
            self.getMessage(1), nick="bar", command="AWAY", params=[]
        )
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")

    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("extended-monitor", "away-notify")
    @pytest.mark.parametrize(
        "monitor_before_connect,cap",
        [
            pytest.param(
                monitor_before_connect,
                cap,
                id=("monitor_before_connect" if monitor_before_connect else "")
                + "-"
                + ("with-cap" if cap else ""),
            )
            for monitor_before_connect in [True, False]
            for cap in [True, False]
        ],
    )
    def testExtendedMonitorAwayNoCap(self, monitor_before_connect, cap):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html
        does nothing when ``away-notify`` is not enabled by the watcher
        """
        if cap:
            self._setupExtendedMonitor(monitor_before_connect, [], ["away-notify"])
        else:
            self._setupExtendedMonitor(monitor_before_connect, [], [])

        self.sendLine(2, "AWAY :afk")
        self.getMessages(2)
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")

        self.sendLine(2, "AWAY")
        self.getMessages(2)
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")

    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("extended-monitor", "setname")
    @pytest.mark.parametrize("monitor_before_connect", [True, False])
    def testExtendedMonitorSetName(self, monitor_before_connect):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html
        with https://ircv3.net/specs/extensions/setname
        """
        self._setupExtendedMonitor(monitor_before_connect, ["setname"], ["setname"])

        self.sendLine(2, "SETNAME :new name")
        self.getMessages(2)
        self.assertMessageMatch(
            self.getMessage(1), nick="bar", command="SETNAME", params=["new name"]
        )
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")

    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("extended-monitor", "setname")
    @pytest.mark.parametrize("monitor_before_connect", [True, False])
    def testExtendedMonitorSetNameNoCap(self, monitor_before_connect):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html
        does nothing when ``setname`` is not enabled by the watcher
        """
        self._setupExtendedMonitor(monitor_before_connect, [], ["setname"])

        self.sendLine(2, "SETNAME :new name")
        self.getMessages(2)
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")


@cases.mark_services
class AuthenticatedExtendedMonitorTestCase(_BaseExtendedMonitorTestCase):
    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("extended-monitor", "account-notify")
    @pytest.mark.parametrize(
        "monitor_before_connect,cap",
        [
            pytest.param(
                monitor_before_connect,
                cap,
                id=("monitor_before_connect" if monitor_before_connect else "")
                + "-"
                + ("with-cap" if cap else ""),
            )
            for monitor_before_connect in [True, False]
            for cap in [True, False]
        ],
    )
    def testExtendedMonitorAccountNotify(self, monitor_before_connect, cap):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html
        does nothing when ``account-notify`` is not enabled by the watcher
        """
        self.controller.registerUser(self, "jilles", "sesame")

        if cap:
            self._setupExtendedMonitor(
                monitor_before_connect,
                ["account-notify"],
                ["account-notify", "sasl", "cap-notify"],
            )
        else:
            self._setupExtendedMonitor(
                monitor_before_connect, ["account-notify"], ["sasl", "cap-notify"]
            )

        self.sendLine(2, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(2, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(
            m,
            command="900",
            fail_msg="Did not send 900 after correct SASL authentication.",
        )
        self.getMessages(2)

        self.assertMessageMatch(
            self.getMessage(1), nick="bar", command="ACCOUNT", params=["jilles"]
        )
        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")

    @cases.mark_specifications("IRCv3")
    @cases.mark_capabilities("extended-monitor", "account-notify")
    @pytest.mark.parametrize(
        "monitor_before_connect,cap",
        [
            pytest.param(
                monitor_before_connect,
                cap,
                id=("monitor_before_connect" if monitor_before_connect else "")
                + "-"
                + ("with-cap" if cap else ""),
            )
            for monitor_before_connect in [True, False]
            for cap in [True, False]
        ],
    )
    def testExtendedMonitorAccountNotifyNoCap(self, monitor_before_connect, cap):
        """Tests https://ircv3.net/specs/extensions/extended-monitor.html
        does nothing when ``account-notify`` is not enabled by the watcher
        """
        self.controller.registerUser(self, "jilles", "sesame")

        if cap:
            self._setupExtendedMonitor(
                monitor_before_connect, [], ["account-notify", "sasl", "cap-notify"]
            )
        else:
            self._setupExtendedMonitor(
                monitor_before_connect, [], ["sasl", "cap-notify"]
            )

        self.sendLine(2, "AUTHENTICATE PLAIN")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(
            m,
            command="AUTHENTICATE",
            params=["+"],
            fail_msg="Sent “AUTHENTICATE PLAIN”, server should have "
            "replied with “AUTHENTICATE +”, but instead sent: {msg}",
        )
        self.sendLine(2, "AUTHENTICATE amlsbGVzAGppbGxlcwBzZXNhbWU=")
        m = self.getRegistrationMessage(2)
        self.assertMessageMatch(
            m,
            command="900",
            fail_msg="Did not send 900 after correct SASL authentication.",
        )
        self.getMessages(2)

        self.assertEqual(self.getMessages(1), [], "watcher got unexpected messages")
