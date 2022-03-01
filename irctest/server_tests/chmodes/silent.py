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
        # mode +s = secret, channel shouldn't show
        # in /quote list UNLESS the user is
        # in the channel.

        # run command LIST
        # if the daemon works correctly, it will reply with
        # , among other things, a 322 (RPL_LIST) line which
        # contains the one channel just created.
        self.sendLine("first", "LIST")
        replies = self.getMessages("first")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(RPL_LIST, reply_cmds)

        # test that another client would not see the secret
        # channel.
        self.connectClient("second", name="second")
        self.getMessages("second")
        self.sendLine("second", "LIST")
        replies = self.getMessages("second")
        reply_cmds = {reply.command for reply in replies}
        # RPL_LIST 322 should NOT be present this time.
        self.assertNotIn(RPL_LIST, reply_cmds)

        # Second client will join the secret channel
        # and call command LIST. The channel SHOULD
        # appear this time.
        self.joinChannel("second", "#gen")
        self.sendLine("second", "LIST")
        replies = self.getMessages("second")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(RPL_LIST, reply_cmds)
        
        
