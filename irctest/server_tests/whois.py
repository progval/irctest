import pytest

from irctest import cases
from irctest.numerics import (
    RPL_AWAY,
    RPL_ENDOFWHOIS,
    RPL_WHOISACCOUNT,
    RPL_WHOISACTUALLY,
    RPL_WHOISCHANNELS,
    RPL_WHOISIDLE,
    RPL_WHOISOPERATOR,
    RPL_WHOISREGNICK,
    RPL_WHOISSECURE,
    RPL_WHOISSERVER,
    RPL_WHOISSPECIAL,
    RPL_WHOISUSER,
)
from irctest.patma import ANYSTR, StrRe


class _WhoisTestMixin(cases.BaseServerTestCase):
    def _testWhoisNumerics(self, authenticate, away):
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
            fail_msg=f"Last message was not RPL_ENDOFWHOIS ({RPL_ENDOFWHOIS})",
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
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR, ANYSTR])
            elif m.command == RPL_WHOISSECURE:
                # TODO: unlikely to ever send this, we should oper up nick2 first
                self.assertMessageMatch(m, params=["nick1", "nick2", ANYSTR])
            else:
                unexpected_messages.append(m)

        self.assertEqual(
            unexpected_messages, [], fail_msg="Unexpected numeric messages: {got}"
        )


class WhoisTestCase(_WhoisTestMixin, cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.mark_specifications("RFC2812")
    def testWhoisUser(self):
        """Test basic WHOIS behavior"""
        nick = "myCoolNick"
        username = "myusernam"  # may be truncated if longer than this
        realname = "My User Name"
        self.addClient()
        self.sendLine(1, f"NICK {nick}")
        self.sendLine(1, f"USER {username} 0 * :{realname}")
        self.skipToWelcome(1)

        self.connectClient("otherNickname")
        self.getMessages(2)
        self.sendLine(2, "WHOIS mycoolnick")
        messages = self.getMessages(2)
        whois_user = messages[0]
        self.assertEqual(whois_user.command, RPL_WHOISUSER)
        #  "<client> <nick> <username> <host> * :<realname>"
        self.assertEqual(whois_user.params[1], nick)
        self.assertIn(whois_user.params[2], ("~" + username, username))
        # dumb regression test for oragono/oragono#355:
        self.assertNotIn(
            whois_user.params[3], [nick, username, "~" + username, realname]
        )
        self.assertEqual(whois_user.params[5], realname)

    @pytest.mark.parametrize("away", [True, False])
    @cases.mark_specifications("Modern")
    def testWhoisNumerics(self, away):
        """Tests all numerics are in the exhaustive list defined in the Modern spec.

        TBD modern PR"""
        self._testWhoisNumerics(authenticate=False, away=away)


@cases.mark_services
class ServicesWhoisTestCase(
    _WhoisTestMixin, cases.BaseServerTestCase, cases.OptionalityHelper
):
    @cases.OptionalityHelper.skipUnlessHasMechanism("PLAIN")
    @cases.mark_specifications("Modern")
    def testWhoisNumerics(self):
        """Tests all numerics are in the exhaustive list defined in the Modern spec,
        on an authenticated user.

        TBD modern PR"""
        self._testWhoisNumerics(authenticate=True, away=False)

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

    @cases.OptionalityHelper.skipUnlessHasMechanism("PLAIN")
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
