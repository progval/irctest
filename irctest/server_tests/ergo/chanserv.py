"""
`Ergo <https://ergo.chat/>`-specific tests of ChanServ and channel
registration functionality.
"""

from irctest import cases, patma
from irctest.controllers.ergo import BASE_CAPS
from irctest.irc_utils.junkdrawer import parse_rplnamreply
from irctest.numerics import ERR_BANNEDFROMCHAN, RPL_TOPIC


@cases.mark_services
class ChanservTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def test_channel_registration(self):
        alice = "alice"
        bob = "bob"
        eve = "eve"
        self.controller.registerUser(self, alice, "alice_password")

        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )
        self.joinChannel(alice, "#alice")

        self.sendLine(alice, "TOPIC #alice :this channel belongs to me, alice")
        self.sendLine(alice, "MODE #alice +b eve!*@*")
        # we'll test that these succeeded after the restart
        self.getMessages(alice)

        self.sendLine(alice, "PRIVMSG chanserv :Register #alice")
        msgs = self.getMessages(alice)
        success = any(
            self.messageEqual(msg, command="MODE", params=["#alice", "+q", "alice"])
            for msg in msgs
        )
        self.assertTrue(
            success,
            f"Did not receive successful MODE +q for registration in response: {msgs}",
        )

        # restart the server. we expect alice's account and channel registration to persist
        self.controller.restart()

        self.connectClient(
            bob,
            name=bob,
            capabilities=BASE_CAPS,
        )
        self.sendLine(bob, "JOIN #alice")
        # alice is not here yet, but bob should not get +o, and he should see the topic
        msgs = self.getMessages(bob)
        self.assertTrue(
            any(
                self.messageEqual(
                    msg,
                    command=RPL_TOPIC,
                    params=["bob", "#alice", "this channel belongs to me, alice"],
                )
                for msg in msgs
            ),
            f"Did not receive expected TOPIC line in response: {msgs}",
        )
        modelines = [msg for msg in msgs if msg.command == "MODE"]
        self.assertEqual(
            modelines,
            [],
            "No MODE lines are expected when joining a registered channel as non-founder",
        )
        self.assertEqual(parse_rplnamreply(msgs), {"bob"})

        self.connectClient(
            alice,
            name=alice,
            account=alice,
            password="alice_password",
            capabilities=BASE_CAPS,
        )

        self.sendLine(alice, "JOIN #alice")
        msgs = self.getMessages(alice)
        self.assertEqual(parse_rplnamreply(msgs), {"bob", "~alice"})

        # test that bans created before the restart are respected
        self.connectClient(eve, name=eve, capabilities=BASE_CAPS)
        self.sendLine(eve, "JOIN #alice")
        msg = self.getMessage(eve)
        self.assertMessageMatch(
            msg, command=ERR_BANNEDFROMCHAN, params=["eve", "#alice", patma.ANYSTR]
        )
