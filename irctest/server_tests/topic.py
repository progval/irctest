"""
The TOPIC command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.1>`__,
`Modern <https://modern.ircdocs.horse/#topic-message>`__)
"""

from irctest import cases, client_mock, runner
from irctest.numerics import ERR_CHANOPRIVSNEEDED, RPL_NOTOPIC, RPL_TOPIC, RPL_TOPICTIME


class TopicTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testTopic(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes […] TOPIC”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient("foo")
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.joinChannel(2, "#chan")

        # clear waiting msgs about cli 2 joining the channel
        self.getMessages(1)
        self.getMessages(2)

        # TODO: check foo is opped OR +t is unset

        self.sendLine(1, "TOPIC #chan :T0P1C")
        try:
            m = self.getMessage(1)
            if m.command == "482":
                raise runner.ImplementationChoice(
                    "Channel creators are not opped by default, and "
                    "channel modes to no allow regular users to change "
                    "topic."
                )
            self.assertMessageMatch(m, command="TOPIC")
        except client_mock.NoMessageException:
            # The RFCs do not say TOPIC must be echoed
            pass
        m = self.getMessage(2)
        self.assertMessageMatch(m, command="TOPIC", params=["#chan", "T0P1C"])

    @cases.mark_specifications("Modern")
    def testTopicUnchanged(self):
        """"If the topic of a channel is changed or cleared, every client in that
        channel (including the author of the topic change) will receive a TOPIC command"
        -- https://modern.ircdocs.horse/#topic-message
        """
        self.connectClient("foo")
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.joinChannel(2, "#chan")

        # clear waiting msgs about cli 2 joining the channel
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "TOPIC #chan :T0P1C")
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, "TOPIC #chan :T0P1C")
        self.assertEqual(self.getMessages(2), [], "Unchanged topic was transmitted")
        self.assertEqual(self.getMessages(1), [], "Unchanged topic was echoed")

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testTopicMode(self):
        """“Once a user has joined a channel, he receives information about
        all commands his server receives affecting the channel.  This
        includes […] TOPIC”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        and <https://tools.ietf.org/html/rfc2812#section-3.2.1>
        """
        self.connectClient("foo")
        self.joinChannel(1, "#chan")

        self.connectClient("bar")
        self.joinChannel(2, "#chan")

        self.getMessages(1)
        self.getMessages(2)

        # TODO: check foo is opped

        self.sendLine(1, "MODE #chan +t")
        self.getMessages(1)

        self.getMessages(2)
        self.sendLine(2, "TOPIC #chan :T0P1C")
        m = self.getMessage(2)
        self.assertMessageMatch(
            m, command="482", fail_msg="Non-op user was not refused use of TOPIC: {msg}"
        )
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(1, "MODE #chan -t")
        self.getMessages(1)
        self.sendLine(2, "TOPIC #chan :T0P1C")
        try:
            m = self.getMessage(2)
            self.assertNotEqual(
                m.command,
                "482",
                msg="User was refused TOPIC whereas +t was not " "set: {}".format(m),
            )
        except client_mock.NoMessageException:
            # The RFCs do not say TOPIC must be echoed
            pass
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="TOPIC", params=["#chan", "T0P1C"])

    @cases.mark_specifications("RFC2812")
    def testTopicNonexistentChannel(self):
        """RFC2812 specifies ERR_NOTONCHANNEL as the correct response to TOPIC
        on a nonexistent channel. The modern spec prefers ERR_NOSUCHCHANNEL.

        <https://tools.ietf.org/html/rfc2812#section-3.2.4>
        <http://modern.ircdocs.horse/#topic-message>
        """
        self.connectClient("foo")
        self.sendLine(1, "TOPIC #chan")
        m = self.getMessage(1)
        # either 403 ERR_NOSUCHCHANNEL or 443 ERR_NOTONCHANNEL
        self.assertIn(m.command, ("403", "443"))

    @cases.mark_specifications("RFC2812")
    def testUnsetTopicResponses(self):
        """Test various cases related to RPL_NOTOPIC with set and unset topics."""
        self.connectClient("bar")
        self.sendLine(1, "JOIN #test")
        messages = self.getMessages(1)
        # shouldn't send RPL_NOTOPIC for a new channel
        self.assertNotIn(RPL_NOTOPIC, [m.command for m in messages])

        self.connectClient("baz")
        self.sendLine(2, "JOIN #test")
        messages = self.getMessages(2)
        # topic is still unset, shouldn't send RPL_NOTOPIC on initial join
        self.assertNotIn(RPL_NOTOPIC, [m.command for m in messages])

        self.sendLine(2, "TOPIC #test")
        messages = self.getMessages(2)
        # explicit TOPIC should receive RPL_NOTOPIC
        self.assertIn(RPL_NOTOPIC, [m.command for m in messages])

        self.getMessages(1)

        self.sendLine(1, "TOPIC #test :new topic")
        # client 1 should get the new TOPIC line echoed
        self.assertMessageMatch(
            self.getMessage(1), command="TOPIC", params=["#test", "new topic"]
        )
        # client 2 should get the new TOPIC line too
        self.assertMessageMatch(
            self.getMessage(2), command="TOPIC", params=["#test", "new topic"]
        )

        # unset the topic:
        self.sendLine(1, "TOPIC #test :")
        # client 1 should get the new TOPIC line echoed, which has the empty arg
        self.assertMessageMatch(
            self.getMessage(1), command="TOPIC", params=["#test", ""]
        )
        # client 2 should get the new TOPIC line to
        self.assertMessageMatch(
            self.getMessage(2), command="TOPIC", params=["#test", ""]
        )

        self.connectClient("qux")
        self.sendLine(3, "join #test")
        messages = self.getMessages(3)
        # topic is once again unset, shouldn't send RPL_NOTOPIC on initial join
        self.assertNotIn(RPL_NOTOPIC, [m.command for m in messages])


class TopicPrivilegesTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812")
    def testTopicPrivileges(self):
        # test the +t channel mode, which prevents unprivileged users
        # from changing the topic
        self.connectClient("bar", name="bar")
        self.joinChannel("bar", "#chan")
        self.getMessages("bar")
        self.sendLine("bar", "MODE #chan +t")
        replies = {msg.command for msg in self.getMessages("bar")}
        # success response is undefined, may be MODE or may be 324 RPL_CHANNELMODEIS,
        # depending on whether this was a no-op
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)
        self.sendLine("bar", "TOPIC #chan :new topic")
        replies = {msg.command for msg in self.getMessages("bar")}
        self.assertIn("TOPIC", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("qux", name="qux")
        self.joinChannel("qux", "#chan")
        self.getMessages("qux")
        self.sendLine("qux", "TOPIC #chan :new topic")
        replies = {msg.command for msg in self.getMessages("qux")}
        self.assertIn(ERR_CHANOPRIVSNEEDED, replies)
        self.assertNotIn("TOPIC", replies)

        self.sendLine("bar", "MODE #chan +v qux")
        replies = {msg.command for msg in self.getMessages("bar")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # regression test: +v cannot change the topic of a +t channel
        self.sendLine("qux", "TOPIC #chan :new topic")
        replies = {msg.command for msg in self.getMessages("qux")}
        self.assertIn(ERR_CHANOPRIVSNEEDED, replies)
        self.assertNotIn("TOPIC", replies)

        # test that RPL_TOPIC and RPL_TOPICTIME are sent on join
        self.connectClient("buzz", name="buzz")
        self.sendLine("buzz", "JOIN #chan")
        replies = self.getMessages("buzz")
        rpl_topic = [msg for msg in replies if msg.command == RPL_TOPIC][0]
        self.assertMessageMatch(
            rpl_topic, command=RPL_TOPIC, params=["buzz", "#chan", "new topic"]
        )
        self.assertEqual(
            len([msg for msg in replies if msg.command == RPL_TOPICTIME]), 1
        )
