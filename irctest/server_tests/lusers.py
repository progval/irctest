"""
The LUSERS command  (`RFC 2812
<https://datatracker.ietf.org/doc/html/rfc2812#section-3.4.2>`__,
`Modern <https://modern.ircdocs.horse/#lusers-message>`__),
which provides statistics on user counts.
"""


from dataclasses import dataclass
import re
from typing import Optional

from irctest import cases
from irctest.numerics import (
    ERR_NOTREGISTERED,
    RPL_GLOBALUSERS,
    RPL_LOCALUSERS,
    RPL_LUSERCHANNELS,
    RPL_LUSERCLIENT,
    RPL_LUSERME,
    RPL_LUSEROP,
    RPL_LUSERUNKNOWN,
    RPL_YOUREOPER,
)
from irctest.patma import ANYSTR, StrRe

# 3 numbers, delimited by spaces, possibly negative (eek)
LUSERCLIENT_REGEX = re.compile(r"^.*( [-0-9]* ).*( [-0-9]* ).*( [-0-9]* ).*$")
# 2 numbers
LUSERME_REGEX = re.compile(r"^.*?( [-0-9]* ).*( [-0-9]* ).*$")


@dataclass
class LusersResult:
    GlobalVisible: Optional[int] = None
    GlobalInvisible: Optional[int] = None
    Servers: Optional[int] = None
    Opers: Optional[int] = None
    Unregistered: Optional[int] = None
    Channels: Optional[int] = None
    LocalTotal: Optional[int] = None
    LocalMax: Optional[int] = None
    GlobalTotal: Optional[int] = None
    GlobalMax: Optional[int] = None


class LusersTestCase(cases.BaseServerTestCase):
    def assertLusersResult(self, lusers, unregistered, total, max_):
        self.assertIn(lusers.Unregistered, (unregistered, None))
        self.assertIn(lusers.GlobalTotal, (total, None))
        self.assertIn(lusers.GlobalMax, (max_, None))

        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertLessEqual(lusers.GlobalInvisible, total)
        self.assertLessEqual(lusers.GlobalVisible, total)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, total)

        self.assertIn(lusers.LocalTotal, (total, None))
        self.assertIn(lusers.LocalMax, (max_, None))

    def getLusers(self, client, allow_missing_265_266):
        self.sendLine(client, "LUSERS")
        messages = self.getMessages(client)
        by_numeric = dict((msg.command, msg) for msg in messages)
        self.assertEqual(len(by_numeric), len(messages), "Duplicated numerics")

        result = LusersResult()

        # all of these take the nick as first param
        for message in messages:
            self.assertEqual(client, message.params[0])

        luserclient = by_numeric[RPL_LUSERCLIENT]  # 251
        self.assertEqual(len(luserclient.params), 2)
        luserclient_param = luserclient.params[1]
        try:
            match = LUSERCLIENT_REGEX.match(luserclient_param)
            result.GlobalVisible = int(match.group(1))
            result.GlobalInvisible = int(match.group(2))
            result.Servers = int(match.group(3))
        except Exception:
            raise ValueError("corrupt reply for 251 RPL_LUSERCLIENT", luserclient_param)

        if RPL_LUSEROP in by_numeric:
            self.assertMessageMatch(
                by_numeric[RPL_LUSEROP], params=[client, StrRe("[0-9]+"), ANYSTR]
            )
            result.Opers = int(by_numeric[RPL_LUSEROP].params[1])
        if RPL_LUSERUNKNOWN in by_numeric:
            self.assertMessageMatch(
                by_numeric[RPL_LUSERUNKNOWN], params=[client, StrRe("[0-9]+"), ANYSTR]
            )
            result.Unregistered = int(by_numeric[RPL_LUSERUNKNOWN].params[1])
        if RPL_LUSERCHANNELS in by_numeric:
            self.assertMessageMatch(
                by_numeric[RPL_LUSERCHANNELS], params=[client, StrRe("[0-9]+"), ANYSTR]
            )
            result.Channels = int(by_numeric[RPL_LUSERCHANNELS].params[1])

        self.assertMessageMatch(by_numeric[RPL_LUSERCLIENT], params=[client, ANYSTR])
        self.assertMessageMatch(by_numeric[RPL_LUSERME], params=[client, ANYSTR])

        if (
            allow_missing_265_266
            and RPL_LOCALUSERS not in by_numeric
            and RPL_GLOBALUSERS not in by_numeric
        ):
            return

        # FIXME: RPL_LOCALUSERS and RPL_GLOBALUSERS are only in Modern, not in RFC2812
        localusers = by_numeric[RPL_LOCALUSERS]
        globalusers = by_numeric[RPL_GLOBALUSERS]
        if len(localusers.params) == 4:
            result.LocalTotal = int(localusers.params[1])
            result.LocalMax = int(localusers.params[2])
            result.GlobalTotal = int(globalusers.params[1])
            result.GlobalMax = int(globalusers.params[2])
        else:
            # Arguments 1 and 2 are optional
            self.assertEqual(len(localusers.params), 2)
            result.LocalTotal = result.LocalMax = None
            result.GlobalTotal = result.GlobalMax = None
            return result

        luserme = by_numeric[RPL_LUSERME]
        self.assertEqual(len(luserme.params), 2)
        luserme_param = luserme.params[1]
        try:
            match = LUSERME_REGEX.match(luserme_param)
            localTotalFromUserme = int(match.group(1))
            serversFromUserme = int(match.group(2))
        except Exception:
            raise ValueError("corrupt reply for 255 RPL_LUSERME", luserme_param)
        self.assertEqual(result.LocalTotal, localTotalFromUserme)
        # serversFromUserme is "servers i'm currently connected to", generally undefined
        self.assertGreaterEqual(serversFromUserme, 0)

        return result


class BasicLusersTestCase(LusersTestCase):
    @cases.mark_specifications("RFC2812")
    def testLusers(self):
        self.connectClient("bar", name="bar")
        self.getLusers("bar", True)

        self.connectClient("qux", name="qux")
        self.getLusers("qux", True)

        self.sendLine("qux", "QUIT")
        self.assertDisconnected("qux")
        self.getLusers("bar", True)

    @cases.mark_specifications("Modern")
    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "snircd"],
        "test depends on Modern behavior, not just RFC2812",
    )
    def testLusersFull(self):
        self.connectClient("bar", name="bar")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=1)

        self.connectClient("qux", name="qux")
        lusers = self.getLusers("qux", False)
        self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)

        self.sendLine("qux", "QUIT")
        self.assertDisconnected("qux")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=2)


class LusersUnregisteredTestCase(LusersTestCase):
    @cases.mark_specifications("RFC2812")
    @cases.xfailIfSoftware(
        ["Nefarious"],
        "Nefarious doesn't seem to distinguish unregistered users from normal ones",
    )
    def testLusersRfc2812(self):
        self.doLusersTest(True)

    @cases.mark_specifications("Modern")
    @cases.xfailIfSoftware(
        ["Nefarious"],
        "Nefarious doesn't seem to distinguish unregistered users from normal ones",
    )
    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "snircd"],
        "test depends on Modern behavior, not just RFC2812",
    )
    def testLusersFull(self):
        self.doLusersTest(False)

    def _synchronize(self, client_name):
        """Synchronizes using a PING, but accept ERR_NOTREGISTERED as a response."""
        self.sendLine(client_name, "PING PARAM")
        for _ in range(1000):
            msg = self.getRegistrationMessage(client_name)
            if msg.command in (ERR_NOTREGISTERED, "PONG"):
                break
        else:
            assert False, (
                "Sent a PING before registration, "
                "got neither PONG or ERR_NOTREGISTERED"
            )

    def doLusersTest(self, allow_missing_265_266):
        self.connectClient("bar", name="bar")
        lusers = self.getLusers("bar", allow_missing_265_266)
        if lusers:
            self.assertLusersResult(lusers, unregistered=0, total=1, max_=1)

        self.addClient("qux")
        self.sendLine("qux", "NICK qux")
        self._synchronize("qux")
        lusers = self.getLusers("bar", allow_missing_265_266)
        if lusers:
            self.assertLusersResult(lusers, unregistered=1, total=1, max_=1)

        self.addClient("bat")
        self.sendLine("bat", "NICK bat")
        self._synchronize("bat")
        lusers = self.getLusers("bar", allow_missing_265_266)
        if lusers:
            self.assertLusersResult(lusers, unregistered=2, total=1, max_=1)

        # complete registration on one client
        self.sendLine("qux", "USER u s e r")
        self.getRegistrationMessage("qux")
        lusers = self.getLusers("bar", allow_missing_265_266)
        if lusers:
            self.assertLusersResult(lusers, unregistered=1, total=2, max_=2)

        # QUIT the other without registering
        self.sendLine("bat", "QUIT")
        self.assertDisconnected("bat")
        lusers = self.getLusers("bar", allow_missing_265_266)
        if lusers:
            self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)


class LusersUnregisteredDefaultInvisibleTestCase(LusersUnregisteredTestCase):
    """Same as above but with +i as the default."""

    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"].update(
                {"default-user-modes": "+i"}
            )
        )

    @cases.mark_specifications("Ergo")
    @cases.xfailIfSoftware(
        ["Nefarious"],
        "Nefarious doesn't seem to distinguish unregistered users from normal ones",
    )
    def testLusers(self):
        self.doLusersTest(False)
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)
        self.assertEqual(lusers.GlobalInvisible, 2)
        self.assertEqual(lusers.GlobalVisible, 0)


class LuserOpersTestCase(LusersTestCase):
    @cases.mark_specifications("Ergo")
    def testLuserOpers(self):
        self.connectClient("bar", name="bar")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=1)
        self.assertIn(lusers.Opers, (0, None))

        # add 1 oper
        self.sendLine("bar", "OPER operuser operpassword")
        msgs = self.getMessages("bar")
        self.assertIn(RPL_YOUREOPER, {msg.command for msg in msgs})
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=1)
        self.assertEqual(lusers.Opers, 1)

        # now 2 opers
        self.connectClient("qux", name="qux")
        self.sendLine("qux", "OPER operuser operpassword")
        self.getMessages("qux")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)
        self.assertEqual(lusers.Opers, 2)

        # remove oper with MODE
        self.sendLine("bar", "MODE bar -o")
        msgs = self.getMessages("bar")
        self.assertIn("MODE", {msg.command for msg in msgs})
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)
        self.assertEqual(lusers.Opers, 1)

        # remove oper by quit
        self.sendLine("qux", "QUIT")
        self.assertDisconnected("qux")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=2)
        self.assertEqual(lusers.Opers, 0)


class ErgoInvisibleDefaultTestCase(LusersTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(
            ergo_config=lambda config: config["accounts"].update(
                {"default-user-modes": "+i"}
            )
        )

    @cases.mark_specifications("Ergo")
    def testLusers(self):
        self.connectClient("bar", name="bar")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=1)
        self.assertEqual(lusers.GlobalInvisible, 1)
        self.assertEqual(lusers.GlobalVisible, 0)

        self.connectClient("qux", name="qux")
        lusers = self.getLusers("qux", False)
        self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)
        self.assertEqual(lusers.GlobalInvisible, 2)
        self.assertEqual(lusers.GlobalVisible, 0)

        # remove +i with MODE
        self.sendLine("bar", "MODE bar -i")
        msgs = self.getMessages("bar")
        lusers = self.getLusers("bar", False)
        self.assertIn("MODE", {msg.command for msg in msgs})
        self.assertLusersResult(lusers, unregistered=0, total=2, max_=2)
        self.assertEqual(lusers.GlobalInvisible, 1)
        self.assertEqual(lusers.GlobalVisible, 1)

        # disconnect invisible user
        self.sendLine("qux", "QUIT")
        self.assertDisconnected("qux")
        lusers = self.getLusers("bar", False)
        self.assertLusersResult(lusers, unregistered=0, total=1, max_=2)
        self.assertEqual(lusers.GlobalInvisible, 0)
        self.assertEqual(lusers.GlobalVisible, 1)
