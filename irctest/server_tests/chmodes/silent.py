from irctest import cases
from irctest.numerics import RPL_LIST

# RPL_LIST = "322"


class SilentWhileJoinedListModeTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testSilentChannelWhileJoined(self):
        # test that a silent channel is shown in list if the user is in the channel.
        self.connectClient("first", name="first")
        self.joinChannel("first", "#gen")
        self.getMessages("first")
        self.sendLine("first", "MODE #gen +s")
        # run command LIST
        self.sendLine("first", "LIST")
        replies = self.getMessages("first")

        # Should be only one line with command RPL_LIST
        listedChannels = [line for line in replies if line.command == RPL_LIST]
        # Just one channel in list.
        self.assertEqual(len(listedChannels), 1)
        # Check that the channel is reported properly
        self.assertMessageMatch(
            listedChannels[0], command=RPL_LIST, params=["first", "#gen", "1", ""]
        )

        # test that another client would not see the secret
        # channel.
        self.connectClient("second", name="second")
        self.getMessages("second")
        self.sendLine("second", "LIST")
        replies = self.getMessages("second")
        # RPL_LIST 322 should NOT be present this time.
        listedChannels = [line for line in replies if line.command == RPL_LIST]
        self.assertEqual(len(listedChannels), 0)

        # Second client will join the secret channel
        # and call command LIST. The channel SHOULD
        # appear this time.
        self.joinChannel("second", "#gen")
        self.sendLine("second", "LIST")
        replies = self.getMessages("second")
        # Should be only one line with command RPL_LIST
        listedChannels = [line for line in replies if line.command == RPL_LIST]
        # Just one channel in list.
        self.assertEqual(len(listedChannels), 1)
        # Check that the channel is reported properly
        self.assertMessageMatch(
            listedChannels[0], command=RPL_LIST, params=["second", "#gen", "2", ""]
        )
