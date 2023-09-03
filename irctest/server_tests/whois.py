"""
The WHOIS command  (`Modern <https://modern.ircdocs.horse/#whois-message>`__)

TODO: cross-reference RFC 1459 and RFC 2812
"""

import pytest

from irctest import cases
from irctest.numerics import (
    RPL_AWAY,
    RPL_ENDOFWHOIS,
    RPL_WHOISACCOUNT,
    RPL_WHOISACTUALLY,
    RPL_WHOISCHANNELS,
    RPL_WHOISHOST,
    RPL_WHOISIDLE,
    RPL_WHOISMODES,
    RPL_WHOISOPERATOR,
    RPL_WHOISREGNICK,
    RPL_WHOISSECURE,
    RPL_WHOISSERVER,
    RPL_WHOISSPECIAL,
    RPL_WHOISUSER,
    RPL_YOUREOPER,
)
from irctest.patma import ANYSTR, StrRe


class _WhoisTestMixin(cases.BaseServerTestCase):
    def _testWhoisNumerics(self, authenticate, away, oper):
        if oper and self.controller.software_name == "Charybdis":
            pytest.xfail("charybdis uses RPL_WHOISSPECIAL instead of RPL_WHOISOPERATOR")

        if authenticate:
            self.connectClient("nick1")
            self.controller.registerUser(self, "val", "sesame")
            self.connectClient(
                "nick2", account="val", password="sesame", capabilities=["sasl"]
            )
        else:
            self.connectClient("nick1")
            self.connectClient("nick2")

        self.sendLine(2, "JOIN #chan1")
        self.sendLine(2, "JOIN #chan2")
        if away:
            self.sendLine(2, "AWAY :I'm on a break")
        self.getMessages(2)

        self.getMessages(1)
        if oper:
            self.sendLine(1, "OPER operuser operpassword")
            self.assertIn(
                RPL_YOUREOPER,
                [m.command for m in self.getMessages(1)],
                fail_msg="OPER failed",
            )

        self.sendLine(1, "WHOIS nick2")

        messages = []
        for _ in range(10):
            messages.extend(self.getMessages(1))
            if RPL_ENDOFWHOIS in (m.command for m in messages):
                break

        last_message = messages.pop()

        self.assertMessageMatch(
            last_message,
            command=RPL_ENDOFWHOIS,
            params=["nick1", "nick2", ANYSTR],
            fail_msg=(
                f"Expected RPL_ENDOFWHOIS ({RPL_ENDOFWHOIS}) as last message, "
                f"got {{msg}}"
            ),
        )

        unexpected_messages = []

        # Straight from the Modern spec
        for m in messages:
            if m.command == RPL_AWAY and away:
                self.assertMessageMatch(m, params=["nick1", "nick2", "I'm on a break"])
            elif m.command == RPL_WHOISREGNICK and authenticate:
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR])
            elif m.command == RPL_WHOISUSER:
                self.assertMessageMatch(
                    m, params=["nick1", "nick2", ANYSTR, ANYSTR, "*", ANYSTR]
                )
            elif m.command == RPL_WHOISCHANNELS:
                self.assertMessageMatch(
                    m,
                    params=[
                        "nick1",
                        "nick2",
                        StrRe("(@#chan1 @#chan2|@#chan2 @#chan1)"),
                    ],
                )
            elif m.command == RPL_WHOISSPECIAL:
                services_controller = self.controller.services_controller
                if (
                    services_controller is not None
                    and services_controller.software_name == "Dlk-Services"
                ):
                    continue
                # Technically allowed, but it's a bad style to use this without
                # explicit configuration by the operators.
                assert False, "RPL_WHOISSPECIAL in use with default configuration"
            elif m.command == RPL_WHOISSERVER:
                self.assertMessageMatch(
                    m, params=["nick1", "nick2", "My.Little.Server", ANYSTR]
                )
            elif m.command == RPL_WHOISOPERATOR:
                # TODO: unlikely to ever send this, we should oper up nick2 first
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR])
            elif m.command == RPL_WHOISIDLE:
                self.assertMessageMatch(
                    m,
                    params=["nick1", "nick2", StrRe("[0-9]+"), StrRe("[0-9]+"), ANYSTR],
                )
            elif m.command == RPL_WHOISACCOUNT and authenticate:
                self.assertMessageMatch(m, params=["nick1", "nick2", "val", ANYSTR])
            elif m.command == RPL_WHOISACTUALLY:
                host_re = "[0-9a-z_:.-]+"
                if len(m.params) == 4:
                    # Most common
                    self.assertMessageMatch(
                        m,
                        params=[
                            "nick1",
                            "nick2",
                            StrRe(host_re),
                            ANYSTR,
                        ],
                    )
                elif len(m.params) == 5:
                    # eg. Hybrid, Unreal
                    self.assertMessageMatch(
                        m,
                        params=[
                            "nick1",
                            "nick2",
                            StrRe(r"(~?username|\*)@" + host_re),
                            StrRe(host_re),
                            ANYSTR,
                        ],
                    )
                elif len(m.params) == 3:
                    # eg. Plexus4
                    self.assertMessageMatch(
                        m,
                        params=[
                            "nick1",
                            "nick2",
                            ANYSTR,
                        ],
                    )
                else:
                    assert (
                        False
                    ), f"Unexpected number of params for RPL_WHOISACTUALLY: {m.params}"
            elif m.command == RPL_WHOISHOST:
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR])
            elif m.command == RPL_WHOISMODES:
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR])
            elif m.command == RPL_WHOISSECURE:
                # TODO: unlikely to ever send this, we should oper up nick2 first
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR])
            else:
                unexpected_messages.append(m)

        self.assertEqual(
            unexpected_messages, [], fail_msg="Unexpected numeric messages: {got}"
        )


class WhoisTestCase(_WhoisTestMixin, cases.BaseServerTestCase):
    @pytest.mark.parametrize(
        "server",
        ["", "My.Little.Server", "coolNick"],
        ids=["no-target", "target_server", "target-nick"],
    )
    @cases.mark_specifications("RFC2812")
    def testWhoisUser(self, server):
        """Test basic WHOIS behavior"""
        nick = "coolNick"
        username = "myusernam"  # may be truncated if longer than this
        realname = "My User Name"
        self.addClient()
        self.sendLine(1, f"NICK {nick}")
        self.sendLine(1, f"USER {username} 0 * :{realname}")
        self.skipToWelcome(1)

        self.connectClient("otherNick")
        self.getMessages(2)
        self.sendLine(2, f"WHOIS {server} {nick}")
        messages = self.getMessages(2)
        whois_user = messages[0]
        self.assertMessageMatch(
            whois_user,
            command=RPL_WHOISUSER,
            # "<client> <nick> <username> <host> * :<realname>"
            params=["otherNick", nick, StrRe("~?" + username), ANYSTR, ANYSTR, realname]
        )
        # dumb regression test for oragono/oragono#355:
        self.assertNotIn(
            whois_user.params[3], [nick, username, "~" + username, realname]
        )

    @pytest.mark.parametrize(
        "away,oper",
        [(False, False), (True, False), (False, True)],
        ids=["normal", "away", "oper"],
    )
    @cases.mark_specifications("Modern")
    def testWhoisNumerics(self, away, oper):
        """Tests all numerics are in the exhaustive list defined in the Modern spec.

        <https://modern.ircdocs.horse/#whois-message>"""
        self._testWhoisNumerics(oper=oper, authenticate=False, away=away)


@cases.mark_services
class ServicesWhoisTestCase(_WhoisTestMixin, cases.BaseServerTestCase):
    @pytest.mark.parametrize("oper", [False, True], ids=["normal", "oper"])
    @cases.skipUnlessHasMechanism("PLAIN")
    @cases.mark_specifications("Modern")
    def testWhoisNumerics(self, oper):
        """Tests all numerics are in the exhaustive list defined in the Modern spec,
        on an authenticated user.

        <https://modern.ircdocs.horse/#whois-message>"""
        self._testWhoisNumerics(oper=oper, authenticate=True, away=False)

    @cases.mark_specifications("Ergo")
    def testInvisibleWhois(self):
        """Test interaction between MODE +i and RPL_WHOISCHANNELS."""
        self.connectClient("userOne")
        self.joinChannel(1, "#xyz")

        self.connectClient("userTwo")
        self.getMessages(2)
        self.sendLine(2, "WHOIS userOne")
        commands = {m.command for m in self.getMessages(2)}
        self.assertIn(
            RPL_WHOISCHANNELS,
            commands,
            "RPL_WHOISCHANNELS should be sent for a non-invisible nick",
        )

        self.getMessages(1)
        self.sendLine(1, "MODE userOne +i")
        message = self.getMessage(1)
        self.assertEqual(
            message.command,
            "MODE",
            "Expected MODE reply, but received {}".format(message.command),
        )
        self.assertEqual(
            message.params,
            ["userOne", "+i"],
            "Expected user set +i, but received {}".format(message.params),
        )

        self.getMessages(2)
        self.sendLine(2, "WHOIS userOne")
        commands = {m.command for m in self.getMessages(2)}
        self.assertNotIn(
            RPL_WHOISCHANNELS,
            commands,
            "RPL_WHOISCHANNELS should not be sent for an invisible nick"
            "unless the user is also a member of the channel",
        )

        self.sendLine(2, "JOIN #xyz")
        self.sendLine(2, "WHOIS userOne")
        commands = {m.command for m in self.getMessages(2)}
        self.assertIn(
            RPL_WHOISCHANNELS,
            commands,
            "RPL_WHOISCHANNELS should be sent for an invisible nick"
            "if the user is also a member of the channel",
        )

        self.sendLine(2, "PART #xyz")
        self.getMessages(2)
        self.getMessages(1)
        self.sendLine(1, "MODE userOne -i")
        message = self.getMessage(1)
        self.assertEqual(
            message.command,
            "MODE",
            "Expected MODE reply, but received {}".format(message.command),
        )
        self.assertEqual(
            message.params,
            ["userOne", "-i"],
            "Expected user set -i, but received {}".format(message.params),
        )

        self.sendLine(2, "WHOIS userOne")
        commands = {m.command for m in self.getMessages(2)}
        self.assertIn(
            RPL_WHOISCHANNELS,
            commands,
            "RPL_WHOISCHANNELS should be sent for a non-invisible nick",
        )

    @cases.skipUnlessHasMechanism("PLAIN")
    @cases.mark_specifications("ircdocs")
    def testWhoisAccount(self):
        """Test numeric 330, RPL_WHOISACCOUNT.

        <https://defs.ircdocs.horse/defs/numerics.html#rpl-whoisaccount-330>"""
        self.controller.registerUser(self, "shivaram", "sesame")
        self.connectClient(
            "netcat", account="shivaram", password="sesame", capabilities=["sasl"]
        )
        self.getMessages(1)

        self.connectClient("curious")
        self.sendLine(2, "WHOIS netcat")
        messages = self.getMessages(2)
        # 330 RPL_WHOISACCOUNT
        whoisaccount = [message for message in messages if message.command == "330"]
        self.assertEqual(len(whoisaccount), 1, messages)
        params = whoisaccount[0].params
        # <client> <nick> <authname> :<info>
        self.assertEqual(len(params), 4)
        self.assertEqual(params[:3], ["curious", "netcat", "shivaram"])

        self.sendLine(1, "WHOIS curious")
        messages = self.getMessages(2)
        whoisaccount = [message for message in messages if message.command == "330"]
        self.assertEqual(len(whoisaccount), 0)
