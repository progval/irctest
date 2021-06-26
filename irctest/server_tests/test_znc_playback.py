import time

from irctest import cases
from irctest.irc_utils.junkdrawer import ircv3_timestamp_to_unixtime, random_name


def extract_playback_privmsgs(messages):
    # convert the output of a playback command, drop the echo message
    result = []
    for msg in messages:
        if msg.command == "PRIVMSG" and msg.params[0].lower() != "*playback":
            result.append(msg.to_history_message())
    return result


class ZncPlaybackTestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        return cases.TestCaseControllerConfig(chathistory=True)

    @cases.mark_specifications("Ergo")
    def testZncPlayback(self):
        early_time = int(time.time() - 60)

        chname = random_name("#znc_channel")
        bar, pw = random_name("bar"), random_name("pass")
        self.controller.registerUser(self, bar, pw)
        self.connectClient(
            bar,
            name=bar,
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
            password=pw,
        )
        self.joinChannel(bar, chname)

        qux = random_name("qux")
        self.connectClient(
            qux,
            name=qux,
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
        )
        self.joinChannel(qux, chname)

        self.sendLine(qux, "PRIVMSG %s :hi there" % (bar,))
        dm = [msg for msg in self.getMessages(qux) if msg.command == "PRIVMSG"][
            0
        ].to_history_message()
        self.assertEqual(dm.text, "hi there")

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            self.sendLine(qux, "PRIVMSG %s :this is message %d" % (chname, i))
            echo_messages.extend(
                msg.to_history_message()
                for msg in self.getMessages(qux)
                if msg.command == "PRIVMSG"
            )
            time.sleep(0.003)
        self.assertEqual(len(echo_messages), NUM_MESSAGES)

        self.getMessages(bar)

        # reattach to 'bar'
        self.connectClient(
            bar,
            name="viewer",
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
            password=pw,
        )
        self.sendLine("viewer", "PRIVMSG *playback :play * %d" % (early_time,))
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(set(messages), set([dm] + echo_messages))
        self.sendLine("viewer", "QUIT")
        self.assertDisconnected("viewer")

        # reattach to 'bar', play back selectively
        self.connectClient(
            bar,
            name="viewer",
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
            password=pw,
        )
        mid_timestamp = ircv3_timestamp_to_unixtime(echo_messages[5].time)
        # exclude message 5 itself (oragono's CHATHISTORY implementation
        # corrects for this, but znc.in/playback does not because whatever)
        mid_timestamp += 0.001
        self.sendLine("viewer", "PRIVMSG *playback :play * %s" % (mid_timestamp,))
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(messages, echo_messages[6:])
        self.sendLine("viewer", "QUIT")
        self.assertDisconnected("viewer")

        # reattach to 'bar', play back selectively (pass a parameter and 2 timestamps)
        self.connectClient(
            bar,
            name="viewer",
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
            password=pw,
        )
        start_timestamp = ircv3_timestamp_to_unixtime(echo_messages[2].time)
        start_timestamp += 0.001
        end_timestamp = ircv3_timestamp_to_unixtime(echo_messages[7].time)
        self.sendLine(
            "viewer",
            "PRIVMSG *playback :play %s %s %s"
            % (chname, start_timestamp, end_timestamp),
        )
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(messages, echo_messages[3:7])
        # test nicknames as targets
        self.sendLine("viewer", "PRIVMSG *playback :play %s %d" % (qux, early_time))
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(messages, [dm])
        self.sendLine(
            "viewer", "PRIVMSG *playback :play %s %d" % (qux.upper(), early_time)
        )
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(messages, [dm])
        self.sendLine("viewer", "QUIT")
        self.assertDisconnected("viewer")

        # test 2-argument form
        self.connectClient(
            bar,
            name="viewer",
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
            password=pw,
        )
        self.sendLine("viewer", "PRIVMSG *playback :play %s" % (chname,))
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(messages, echo_messages)
        self.sendLine("viewer", "PRIVMSG *playback :play *")
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        self.assertEqual(set(messages), set([dm] + echo_messages))
        self.sendLine("viewer", "QUIT")
        self.assertDisconnected("viewer")

        # test limiting behavior
        config = self.controller.getConfig()
        config["history"]["znc-maxmessages"] = 5
        self.controller.rehash(self, config)
        self.connectClient(
            bar,
            name="viewer",
            capabilities=[
                "batch",
                "labeled-response",
                "message-tags",
                "server-time",
                "echo-message",
                "sasl",
            ],
            password=pw,
        )
        self.sendLine(
            "viewer", "PRIVMSG *playback :play %s %d" % (chname, int(time.time() - 60))
        )
        messages = extract_playback_privmsgs(self.getMessages("viewer"))
        # should receive the latest 5 messages
        self.assertEqual(messages, echo_messages[5:])
