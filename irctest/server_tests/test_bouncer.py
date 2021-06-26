from irctest import cases
from irctest.irc_utils.sasl import sasl_plain_blob
from irctest.numerics import ERR_NICKNAMEINUSE, RPL_WELCOME
from irctest.patma import ANYSTR, StrRe


class Bouncer(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testBouncer(self):
        """Test basic bouncer functionality."""
        self.controller.registerUser(self, "observer", "observerpassword")
        self.controller.registerUser(self, "testuser", "mypassword")

        self.connectClient(
            "observer", password="observerpassword", capabilities=["sasl"]
        )
        self.joinChannel(1, "#chan")
        self.sendLine(1, "CAP REQ :message-tags server-time")
        self.getMessages(1)

        self.addClient()
        self.sendLine(2, "CAP LS 302")
        self.sendLine(2, "AUTHENTICATE PLAIN")
        self.sendLine(2, sasl_plain_blob("testuser", "mypassword"))
        self.sendLine(2, "NICK testnick")
        self.sendLine(2, "USER a 0 * a")
        self.sendLine(2, "CAP REQ :server-time message-tags")
        self.sendLine(2, "CAP END")
        messages = self.getMessages(2)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 1)
        # should see a regburst for testnick
        self.assertMessageMatch(welcomes[0], params=["testnick", ANYSTR])
        self.joinChannel(2, "#chan")

        self.addClient()
        self.sendLine(3, "CAP LS 302")
        self.sendLine(3, "AUTHENTICATE PLAIN")
        self.sendLine(3, sasl_plain_blob("testuser", "mypassword"))
        self.sendLine(3, "NICK testnick")
        self.sendLine(3, "USER a 0 * a")
        self.sendLine(3, "CAP REQ :server-time message-tags account-tag")
        self.sendLine(3, "CAP END")
        messages = self.getMessages(3)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 1)
        # should see the *same* regburst for testnick
        self.assertMessageMatch(welcomes[0], params=["testnick", ANYSTR])
        joins = [message for message in messages if message.command == "JOIN"]
        # we should be automatically joined to #chan
        self.assertMessageMatch(joins[0], params=["#chan"])

        # disable multiclient in nickserv
        self.sendLine(3, "NS SET MULTICLIENT OFF")
        self.getMessages(3)

        self.addClient()
        self.sendLine(4, "CAP LS 302")
        self.sendLine(4, "AUTHENTICATE PLAIN")
        self.sendLine(4, sasl_plain_blob("testuser", "mypassword"))
        self.sendLine(4, "NICK testnick")
        self.sendLine(4, "USER a 0 * a")
        self.sendLine(4, "CAP REQ :server-time message-tags")
        self.sendLine(4, "CAP END")
        # with multiclient disabled, we should not be able to attach to the nick
        messages = self.getMessages(4)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 0)
        errors = [
            message for message in messages if message.command == ERR_NICKNAMEINUSE
        ]
        self.assertEqual(len(errors), 1)

        self.sendLine(3, "NS SET MULTICLIENT ON")
        self.getMessages(3)
        self.addClient()
        self.sendLine(5, "CAP LS 302")
        self.sendLine(5, "AUTHENTICATE PLAIN")
        self.sendLine(5, sasl_plain_blob("testuser", "mypassword"))
        self.sendLine(5, "NICK testnick")
        self.sendLine(5, "USER a 0 * a")
        self.sendLine(5, "CAP REQ server-time")
        self.sendLine(5, "CAP END")
        messages = self.getMessages(5)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 1)

        self.sendLine(1, "@+clientOnlyTag=Value PRIVMSG #chan :hey")
        self.getMessages(1)
        messagesfortwo = [
            msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"
        ]
        messagesforthree = [
            msg for msg in self.getMessages(3) if msg.command == "PRIVMSG"
        ]
        self.assertEqual(len(messagesfortwo), 1)
        self.assertEqual(len(messagesforthree), 1)
        messagefortwo = messagesfortwo[0]
        messageforthree = messagesforthree[0]
        messageforfive = self.getMessage(5)
        self.assertMessageMatch(messagefortwo, params=["#chan", "hey"])
        self.assertMessageMatch(messageforthree, params=["#chan", "hey"])
        self.assertMessageMatch(messageforfive, params=["#chan", "hey"])
        self.assertIn("time", messagefortwo.tags)
        self.assertIn("time", messageforthree.tags)
        self.assertIn("time", messageforfive.tags)
        # 3 has account-tag
        self.assertIn("account", messageforthree.tags)
        # should get same msgid
        self.assertEqual(messagefortwo.tags["msgid"], messageforthree.tags["msgid"])
        # 5 only has server-time, shouldn't get account or msgid tags
        self.assertNotIn("account", messageforfive.tags)
        self.assertNotIn("msgid", messageforfive.tags)

        # test that copies of sent messages go out to other sessions
        self.sendLine(2, "PRIVMSG observer :this is a direct message")
        self.getMessages(2)
        messageForRecipient = [
            msg for msg in self.getMessages(1) if msg.command == "PRIVMSG"
        ][0]
        copyForOtherSession = [
            msg for msg in self.getMessages(3) if msg.command == "PRIVMSG"
        ][0]
        self.assertEqual(messageForRecipient.params, copyForOtherSession.params)
        self.assertEqual(
            messageForRecipient.tags["msgid"], copyForOtherSession.tags["msgid"]
        )

        self.sendLine(2, "QUIT :two out")
        quitLines = [msg for msg in self.getMessages(2) if msg.command == "QUIT"]
        self.assertEqual(len(quitLines), 1)
        self.assertMessageMatch(quitLines[0], params=[StrRe(".*two out.*")])
        # neither the observer nor the other attached session should see a quit here
        quitLines = [msg for msg in self.getMessages(1) if msg.command == "QUIT"]
        self.assertEqual(quitLines, [])
        quitLines = [msg for msg in self.getMessages(3) if msg.command == "QUIT"]
        self.assertEqual(quitLines, [])

        # session 3 should be untouched at this point
        self.sendLine(1, "@+clientOnlyTag=Value PRIVMSG #chan :hey again")
        self.getMessages(1)
        messagesforthree = [
            msg for msg in self.getMessages(3) if msg.command == "PRIVMSG"
        ]
        self.assertEqual(len(messagesforthree), 1)
        self.assertMessageMatch(
            messagesforthree[0], command="PRIVMSG", params=["#chan", "hey again"]
        )

        self.sendLine(5, "QUIT :five out")
        self.getMessages(5)
        self.sendLine(3, "QUIT :three out")
        quitLines = [msg for msg in self.getMessages(3) if msg.command == "QUIT"]
        self.assertEqual(len(quitLines), 1)
        self.assertMessageMatch(quitLines[0], params=[StrRe(".*three out.*")])
        # observer should see *this* quit
        quitLines = [msg for msg in self.getMessages(1) if msg.command == "QUIT"]
        self.assertEqual(len(quitLines), 1)
        self.assertMessageMatch(quitLines[0], params=[StrRe(".*three out.*")])
