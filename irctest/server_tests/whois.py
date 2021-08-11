from irctest import cases
from irctest.numerics import RPL_WHOISCHANNELS, RPL_WHOISUSER


@cases.mark_services
class WhoisTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.mark_specifications("RFC2812")
    def testWhoisUser(self):
        """Test basic WHOIS behavior"""
        nick = "myCoolNickname"
        username = "myUsernam"  # may be truncated if longer than this
        realname = "My Real Name"
        self.addClient()
        self.sendLine(1, f"NICK {nick}")
        self.sendLine(1, f"USER {username} 0 * :{realname}")
        self.skipToWelcome(1)

        self.connectClient("otherNickname")
        self.getMessages(2)
        self.sendLine(2, "WHOIS mycoolnickname")
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
