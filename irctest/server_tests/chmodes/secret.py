from irctest import cases
from irctest.numerics import RPL_LIST


class SecretChannelTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459")
    def testSecretChannelListCommand(self):
        """
        <https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.6>

        "Likewise, secret channels are not listed
        at all unless the client is a member of the channel in question."
        """

        def get_listed_channels(replies):
            channels = set()
            for reply in replies:
                # skip pseudo-channels (&SERVER, &NOTICES) listed by ngircd
                # and ircu:
                if reply.command == RPL_LIST and reply.params[1].startswith("#"):
                    channels.add(reply.params[1])
            return channels

        # test that a silent channel is shown in list if the user is in the channel.
        self.connectClient("first", name="first")
        self.joinChannel("first", "#gen")
        self.getMessages("first")
        self.sendLine("first", "MODE #gen +s")
        # run command LIST
        self.sendLine("first", "LIST")
        replies = self.getMessages("first")
        self.assertEqual(get_listed_channels(replies), {"#gen"})

        # test that another client would not see the secret
        # channel.
        self.connectClient("second", name="second")
        self.getMessages("second")
        self.sendLine("second", "LIST")
        replies = self.getMessages("second")
        # RPL_LIST 322 should NOT be present this time.
        self.assertEqual(get_listed_channels(replies), set())

        # Second client will join the secret channel
        # and call command LIST. The channel SHOULD
        # appear this time.
        self.joinChannel("second", "#gen")
        self.sendLine("second", "LIST")
        replies = self.getMessages("second")
        # Should be only one line with command RPL_LIST
        self.assertEqual(get_listed_channels(replies), {"#gen"})
