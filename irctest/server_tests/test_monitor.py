"""
<http://ircv3.net/specs/core/monitor-3.2.html>
"""

from irctest import cases
from irctest.client_mock import NoMessageException
from irctest.basecontrollers import NotImplementedByController

class EchoMessageTestCase(cases.BaseServerTestCase):
    def check_server_support(self):
        if 'MONITOR' not in self.server_support:
            raise NotImplementedByController('MONITOR')

    def assertMononline(self, client, nick, m=None):
        if not m:
            m = self.getMessage(client)
        self.assertMessageEqual(m, command='730', # RPL_MONONLINE
                fail_msg='Sent non-730 (RPL_MONONLINE) message after '
                'monitored nick “{}” connected: {msg}',
                extra_format=(nick,))
        self.assertEqual(len(m.params), 2, m,
                fail_msg='Invalid number of params of RPL_MONONLINE: {msg}')
        self.assertEqual(m.params[1].split('!')[0], 'bar',
                fail_msg='730 (RPL_MONONLINE) with bad target after “{}” '
                'connects: {msg}',
                extra_format=(nick,))

    def assertMonoffline(self, client, nick, m=None):
        if not m:
            m = self.getMessage(client)
        self.assertMessageEqual(m, command='731', # RPL_MONOFFLINE
                fail_msg='Did not reply with 731 (RPL_MONOFFLINE) to '
                '“MONITOR + {}”, while “{}” is offline: {msg}',
                extra_format=(nick, nick))
        self.assertEqual(len(m.params), 2, m,
                fail_msg='Invalid number of params of RPL_MONOFFLINE: {msg}')
        self.assertEqual(m.params[1].split('!')[0], 'bar',
                fail_msg='731 (RPL_MONOFFLINE) reply to “MONITOR + {}” '
                'with bad target: {msg}',
                extra_format=(nick,))

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testMonitorOneDisconnected(self):
        """“If any of the targets being added are online, the server will
        generate RPL_MONONLINE numerics listing those targets that are
        online.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor--targettarget2>
        """
        self.connectClient('foo')
        self.check_server_support()
        self.sendLine(1, 'MONITOR + bar')
        self.assertMonoffline(1, 'bar')
        self.connectClient('bar')
        self.assertMononline(1, 'bar')
        self.sendLine(2, 'QUIT :bye')
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertMonoffline(1, 'bar')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testMonitorOneConnection(self):
        self.connectClient('foo')
        self.check_server_support()
        self.sendLine(1, 'MONITOR + bar')
        self.getMessages(1)
        self.connectClient('bar')
        self.assertMononline(1, 'bar')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testMonitorOneConnected(self):
        """“If any of the targets being added are offline, the server will
        generate RPL_MONOFFLINE numerics listing those targets that are
        online.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor--targettarget2>
        """
        self.connectClient('foo')
        self.check_server_support()
        self.connectClient('bar')
        self.sendLine(1, 'MONITOR + bar')
        self.assertMononline(1, 'bar')
        self.sendLine(2, 'QUIT :bye')
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertMonoffline(1, 'bar')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testMonitorOneConnection(self):
        self.connectClient('foo')
        self.check_server_support()
        self.connectClient('bar')
        self.sendLine(1, 'MONITOR + bar')
        self.assertMononline(1, 'bar')
        self.sendLine(2, 'QUIT :bye')
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertMonoffline(1, 'bar')
        self.connectClient('bar')
        self.assertMononline(1, 'bar')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testMonitorConnectedAndDisconnected(self):
        """“If any of the targets being added are online, the server will
        generate RPL_MONONLINE numerics listing those targets that are
        online.

        If any of the targets being added are offline, the server will
        generate RPL_MONOFFLINE numerics listing those targets that are
        online.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor--targettarget2>
        """
        self.connectClient('foo')
        self.check_server_support()
        self.connectClient('bar')
        self.sendLine(1, 'MONITOR + bar,baz')
        m1 = self.getMessage(1)
        m2 = self.getMessage(1)
        commands = {m1.command, m2.command}
        self.assertEqual(commands, {'730', '731'},
                fail_msg='Did not send one 730 (RPL_MONONLINE) and one '
                '731 (RPL_MONOFFLINE) after “MONITOR + bar,baz” when “bar” '
                'is online and “baz” is offline. Sent this instead: {}',
                extra_format=((m1, m2)))
        if m1.command == '731':
            (m1, m2) = (m2, m1)
        self.assertEqual(len(m1.params), 2, m1,
                fail_msg='Invalid number of params of RPL_MONONLINE: {msg}')
        self.assertEqual(len(m2.params), 2, m2,
                fail_msg='Invalid number of params of RPL_MONONLINE: {msg}')
        self.assertEqual(m1.params[1].split('!')[0], 'bar', m1,
                fail_msg='730 (RPL_MONONLINE) with bad target after '
                '“MONITOR + bar,baz” and “bar” is connected: {msg}')
        self.assertEqual(m2.params[1].split('!')[0], 'baz', m2,
                fail_msg='731 (RPL_MONOFFLINE) with bad target after '
                '“MONITOR + bar,baz” and “baz” is disconnected: {msg}')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testUnmonitor(self):
        self.connectClient('foo')
        self.check_server_support()
        self.sendLine(1, 'MONITOR + bar')
        self.getMessages(1)
        self.connectClient('bar')
        self.assertMononline(1, 'bar')
        self.sendLine(1, 'MONITOR - bar')
        self.assertEqual(self.getMessages(1), [],
                fail_msg='Got messages after “MONITOR - bar”: {got}')
        self.sendLine(2, 'QUIT :bye')
        try:
            self.getMessages(2)
        except ConnectionResetError:
            pass
        self.assertEqual(self.getMessages(1), [],
                fail_msg='Got messages after disconnection of unmonitored '
                'nick: {got}')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testMonitorForbidsMasks(self):
        """“The MONITOR implementation also enhances user privacy by
        disallowing subscription to hostmasks, allowing users to avoid
        nick-change stalking.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#watch-vs-monitor>

        “For this specification, ‘target’ MUST be a valid nick as determined
        by the IRC daemon.”
        -- <http://ircv3.net/specs/core/monitor-3.2.html#monitor-command>
        """
        self.connectClient('foo')
        self.check_server_support()
        self.sendLine(1, 'MONITOR + *!username@localhost')
        self.sendLine(1, 'MONITOR + *!username@127.0.0.1')
        try:
            m = self.getMessage(1)
            self.assertNotEqual(m.command, '731', m,
                    fail_msg='Got 731 (RPL_MONOFFLINE) after adding a monitor '
                    'on a mask: {msg}')
        except NoMessageException:
            pass
        self.connectClient('bar')
        try:
            m = self.getMessage(1)
        except NoMessageException:
            pass
        else:
            raise AssertionError('Got message after client whose MONITORing '
                    'was requested via hostmask connected: {}'.format(m))

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testTwoMonitoringOneRemove(self):
        """Tests the following scenario:
        * foo MONITORs qux
        * bar MONITORs qux
        * bar unMONITORs qux
        * qux connects.
        """
        self.connectClient('foo')
        self.check_server_support()
        self.connectClient('bar')
        self.sendLine(1, 'MONITOR + qux')
        self.sendLine(2, 'MONITOR + qux')
        self.getMessages(1)
        self.getMessages(2)
        self.sendLine(2, 'MONITOR - qux')
        l = self.getMessages(2)
        self.assertEqual(l, [],
                fail_msg='Got response to “MONITOR -”: {}',
                extra_format=(l,))
        self.connectClient('qux')
        self.getMessages(3)
        l = self.getMessages(1)
        self.assertNotEqual(l, [],
                fail_msg='Received no message after MONITORed client '
                'connects.')
        l = self.getMessages(2)
        self.assertEqual(l, [],
                fail_msg='Got response to unmonitored client: {}',
                extra_format=(l,))
