"""
`Ergo <https://ergo.chat/>`_-specific tests of
`multiclient features
<https://github.com/ergochat/ergo/blob/master/docs/MANUAL.md#multiclient-bouncer>`_
"""

from irctest import cases
from irctest.irc_utils.sasl import sasl_plain_blob
from irctest.numerics import ERR_NICKNAMEINUSE, RPL_WELCOME
from irctest.patma import ANYSTR, StrRe


@cases.mark_services
class BouncerTestCase(cases.BaseServerTestCase):
    def setUp(self):
        super().setUp()
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

    def _connectClient3(self):
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

    def _connectClient4(self):
        # connect a client similar to 3, but without the message-tags and account-tag
        # capabilities, to make sure it does not receive the associated tags
        self.addClient()
        self.sendLine(4, "CAP LS 302")
        self.sendLine(4, "AUTHENTICATE PLAIN")
        self.sendLine(4, sasl_plain_blob("testuser", "mypassword"))
        self.sendLine(4, "NICK testnick")
        self.sendLine(4, "USER a 0 * a")
        self.sendLine(4, "CAP REQ server-time")
        self.sendLine(4, "CAP END")
        messages = self.getMessages(4)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 1)

    @cases.mark_specifications("Ergo")
    def testAutomaticResumption(self):
        """Test logging into an account that already has a client joins the client's session"""
        self._connectClient3()

    @cases.mark_specifications("Ergo")
    def testChannelMessageFromOther(self):
        """Test that all clients attached to a session get messages sent by someone else
        to a channel"""
        self._connectClient3()
        self._connectClient4()

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
        messageforfour = self.getMessage(4)
        self.assertMessageMatch(messagefortwo, params=["#chan", "hey"])
        self.assertMessageMatch(messageforthree, params=["#chan", "hey"])
        self.assertMessageMatch(messageforfour, params=["#chan", "hey"])
        self.assertIn("time", messagefortwo.tags)
        self.assertIn("time", messageforthree.tags)
        self.assertIn("time", messageforfour.tags)
        # 3 has account-tag
        self.assertIn("account", messageforthree.tags)
        # should get same msgid
        self.assertEqual(messagefortwo.tags["msgid"], messageforthree.tags["msgid"])
        # 4 only has server-time, shouldn't get account or msgid tags
        self.assertNotIn("account", messageforfour.tags)
        self.assertNotIn("msgid", messageforfour.tags)

    @cases.mark_specifications("Ergo")
    def testChannelMessageFromSelf(self):
        """Test that all clients attached to a session get messages sent by someone else
        to a channel"""
        self._connectClient3()
        self._connectClient4()

        self.sendLine(2, "@+clientOnlyTag=Value PRIVMSG #chan :hey")
        messagesfortwo = [
            msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"
        ]
        messagesforone = [
            msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"
        ]
        messagesforthree = [
            msg for msg in self.getMessages(3) if msg.command == "PRIVMSG"
        ]
        self.assertEqual(len(messagesforone), 1)
        self.assertEqual(len(messagesfortwo), 0)  # echo-message not enabled
        self.assertEqual(len(messagesforthree), 1)
        messageforone = messagesforone[0]
        messageforthree = messagesforthree[0]
        messageforfour = self.getMessage(4)
        self.assertMessageMatch(messageforone, params=["#chan", "hey"])
        self.assertMessageMatch(messageforthree, params=["#chan", "hey"])
        self.assertMessageMatch(messageforfour, params=["#chan", "hey"])
        self.assertIn("time", messageforone.tags)
        self.assertIn("time", messageforthree.tags)
        self.assertIn("time", messageforfour.tags)
        # 3 has account-tag
        self.assertIn("account", messageforthree.tags)
        # should get same msgid
        self.assertEqual(messageforone.tags["msgid"], messageforthree.tags["msgid"])
        # 4 only has server-time, shouldn't get account or msgid tags
        self.assertNotIn("account", messageforfour.tags)
        self.assertNotIn("msgid", messageforfour.tags)

    @cases.mark_specifications("Ergo")
    def testDirectMessageFromOther(self):
        """Test that all clients attached to a session get copies of messages sent
        by an other client of that session directly to an other user"""
        self._connectClient3()
        self._connectClient4()

        self.sendLine(1, "PRIVMSG testnick :this is a direct message")
        self.getMessages(1)
        messagefortwo = [
            msg for msg in self.getMessages(2) if msg.command == "PRIVMSG"
        ][0]
        messageforthree = [
            msg for msg in self.getMessages(3) if msg.command == "PRIVMSG"
        ][0]
        self.assertEqual(messagefortwo.params, messageforthree.params)
        self.assertEqual(messagefortwo.tags["msgid"], messageforthree.tags["msgid"])

    @cases.mark_specifications("Ergo")
    def testDirectMessageFromSelf(self):
        """Test that all clients attached to a session get copies of messages sent
        by an other client of that session directly to an other user"""
        self._connectClient3()
        self._connectClient4()

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

    @cases.mark_specifications("Ergo")
    def testQuit(self):
        """Test that a single client of a session does not make the whole user quit
        (and is generally not visible to anyone else, not even their other sessions),
        until the last client quits"""
        self._connectClient3()
        self._connectClient4()
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

        self.sendLine(4, "QUIT :four out")
        self.getMessages(4)
        self.sendLine(3, "QUIT :three out")
        quitLines = [msg for msg in self.getMessages(3) if msg.command == "QUIT"]
        self.assertEqual(len(quitLines), 1)
        self.assertMessageMatch(quitLines[0], params=[StrRe(".*three out.*")])
        # observer should see *this* quit
        quitLines = [msg for msg in self.getMessages(1) if msg.command == "QUIT"]
        self.assertEqual(len(quitLines), 1)
        self.assertMessageMatch(quitLines[0], params=[StrRe(".*three out.*")])

    @cases.mark_specifications("Ergo")
    def testDisableAutomaticResumption(self):
        # disable multiclient in nickserv
        self.sendLine(2, "NS SET MULTICLIENT OFF")
        self.getMessages(2)

        self.addClient()
        self.sendLine(3, "CAP LS 302")
        self.sendLine(3, "AUTHENTICATE PLAIN")
        self.sendLine(3, sasl_plain_blob("testuser", "mypassword"))
        self.sendLine(3, "NICK testnick")
        self.sendLine(3, "USER a 0 * a")
        self.sendLine(3, "CAP REQ :server-time message-tags")
        self.sendLine(3, "CAP END")
        # with multiclient disabled, we should not be able to attach to the nick
        messages = self.getMessages(3)
        welcomes = [message for message in messages if message.command == RPL_WELCOME]
        self.assertEqual(len(welcomes), 0)
        errors = [
            message for message in messages if message.command == ERR_NICKNAMEINUSE
        ]
        self.assertEqual(len(errors), 1)
