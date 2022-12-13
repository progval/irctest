"""
`Ergo <https://ergo.chat/>`_-specific tests of auditorium mode

TODO: Should be extended to other servers, once a specification is written.
"""

import math
import time

from irctest import cases
from irctest.irc_utils.junkdrawer import ircv3_timestamp_to_unixtime
from irctest.numerics import RPL_NAMREPLY

MODERN_CAPS = [
    "server-time",
    "message-tags",
    "batch",
    "labeled-response",
    "echo-message",
    "account-tag",
]


class AuditoriumTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testAuditorium(self):
        self.connectClient("bar", name="bar", capabilities=MODERN_CAPS)
        self.joinChannel("bar", "#auditorium")
        self.getMessages("bar")
        self.sendLine("bar", "MODE #auditorium +u")
        modelines = [msg for msg in self.getMessages("bar") if msg.command == "MODE"]
        self.assertEqual(len(modelines), 1)
        self.assertMessageMatch(modelines[0], params=["#auditorium", "+u"])

        self.connectClient("guest1", name="guest1", capabilities=MODERN_CAPS)
        self.joinChannel("guest1", "#auditorium")
        self.getMessages("guest1")
        # chanop should get a JOIN message
        join_msgs = [msg for msg in self.getMessages("bar") if msg.command == "JOIN"]
        self.assertEqual(len(join_msgs), 1)
        self.assertMessageMatch(join_msgs[0], nick="guest1", params=["#auditorium"])

        self.connectClient("guest2", name="guest2", capabilities=MODERN_CAPS)
        self.joinChannel("guest2", "#auditorium")
        self.getMessages("guest2")
        # chanop should get a JOIN message
        join_msgs = [msg for msg in self.getMessages("bar") if msg.command == "JOIN"]
        self.assertEqual(len(join_msgs), 1)
        join_msg = join_msgs[0]
        self.assertMessageMatch(join_msg, nick="guest2", params=["#auditorium"])
        # oragono/oragono#1642 ; msgid should be populated,
        # and the time tag should be sane
        self.assertTrue(join_msg.tags.get("msgid"))
        self.assertLessEqual(
            math.fabs(time.time() - ircv3_timestamp_to_unixtime(join_msg.tags["time"])),
            60.0,
        )
        # fellow unvoiced participant should not
        unvoiced_join_msgs = [
            msg for msg in self.getMessages("guest1") if msg.command == "JOIN"
        ]
        self.assertEqual(len(unvoiced_join_msgs), 0)

        self.connectClient("guest3", name="guest3", capabilities=MODERN_CAPS)
        self.joinChannel("guest3", "#auditorium")
        self.getMessages("guest3")

        self.sendLine("bar", "PRIVMSG #auditorium hi")
        echo_message = [
            msg for msg in self.getMessages("bar") if msg.command == "PRIVMSG"
        ][0]
        self.assertEqual(echo_message, self.getMessages("guest1")[0])
        self.assertEqual(echo_message, self.getMessages("guest2")[0])
        self.assertEqual(echo_message, self.getMessages("guest3")[0])

        # unvoiced users can speak
        self.sendLine("guest1", "PRIVMSG #auditorium :hi you")
        echo_message = [
            msg for msg in self.getMessages("guest1") if msg.command == "PRIVMSG"
        ][0]
        self.assertEqual(self.getMessages("bar"), [echo_message])
        self.assertEqual(self.getMessages("guest2"), [echo_message])
        self.assertEqual(self.getMessages("guest3"), [echo_message])

        def names(client):
            self.sendLine(client, "NAMES #auditorium")
            result = set()
            for msg in self.getMessages(client):
                if msg.command == RPL_NAMREPLY:
                    result.update(msg.params[-1].split())
            return result

        self.assertEqual(names("bar"), {"@bar", "guest1", "guest2", "guest3"})
        self.assertEqual(names("guest1"), {"@bar"})
        self.assertEqual(names("guest2"), {"@bar"})
        self.assertEqual(names("guest3"), {"@bar"})

        self.sendLine("bar", "MODE #auditorium +v guest1")
        modeLine = [msg for msg in self.getMessages("bar") if msg.command == "MODE"][0]
        self.assertEqual(self.getMessages("guest1"), [modeLine])
        self.assertEqual(self.getMessages("guest2"), [modeLine])
        self.assertEqual(self.getMessages("guest3"), [modeLine])
        self.assertEqual(names("bar"), {"@bar", "+guest1", "guest2", "guest3"})
        self.assertEqual(names("guest2"), {"@bar", "+guest1"})
        self.assertEqual(names("guest3"), {"@bar", "+guest1"})

        self.sendLine("guest1", "PART #auditorium")
        part = [msg for msg in self.getMessages("guest1") if msg.command == "PART"][0]
        # everyone should see voiced PART
        self.assertEqual(self.getMessages("bar")[0], part)
        self.assertEqual(self.getMessages("guest2")[0], part)
        self.assertEqual(self.getMessages("guest3")[0], part)

        self.joinChannel("guest1", "#auditorium")
        self.getMessages("guest1")
        self.getMessages("bar")

        self.sendLine("guest2", "PART #auditorium")
        part = [msg for msg in self.getMessages("guest2") if msg.command == "PART"][0]
        self.assertEqual(self.getMessages("bar"), [part])
        # part should be hidden from unvoiced participants
        self.assertEqual(self.getMessages("guest1"), [])
        self.assertEqual(self.getMessages("guest3"), [])

        self.sendLine("guest3", "QUIT")
        self.assertDisconnected("guest3")
        # quit should be hidden from unvoiced participants
        self.assertEqual(
            len([msg for msg in self.getMessages("bar") if msg.command == "QUIT"]), 1
        )
        self.assertEqual(
            len([msg for msg in self.getMessages("guest1") if msg.command == "QUIT"]), 0
        )
