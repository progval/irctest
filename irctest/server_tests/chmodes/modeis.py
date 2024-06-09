from irctest import cases
from irctest.numerics import RPL_CHANNELCREATED, RPL_CHANNELMODEIS
from irctest.patma import ANYSTR, ListRemainder


class RplChannelModeIsTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testChannelModeIs(self):
        """Test RPL_CHANNELMODEIS and RPL_CHANNELCREATED as responses to
        `MODE #channel`:
        <https://modern.ircdocs.horse/#rplcreationtime-329>
        <https://modern.ircdocs.horse/#rplchannelmodeis-324>
        """
        expected_numerics = {RPL_CHANNELMODEIS, RPL_CHANNELCREATED}
        if self.controller.software_name in ("irc2", "Sable"):
            # irc2 and Sable don't use timestamps for conflict resolution,
            # consequently they don't store the channel creation timestamp
            # and don't send RPL_CHANNELCREATED
            expected_numerics = {RPL_CHANNELMODEIS}

        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        # i, n, and t are specified by RFC1459; some of them may be on by default,
        # but after this, at least those three should be enabled:
        self.sendLine("chanop", "MODE #chan +int")
        self.getMessages("chanop")

        self.sendLine("chanop", "MODE #chan")
        messages = self.getMessages("chanop")
        self.assertLessEqual(expected_numerics, {msg.command for msg in messages})
        for message in messages:
            if message.command == RPL_CHANNELMODEIS:
                # the final parameters are the mode string (e.g. `+int`),
                # and then optionally any mode parameters (in case the ircd
                # lists a mode that takes a parameter)
                self.assertMessageMatch(
                    message,
                    command=RPL_CHANNELMODEIS,
                    params=["chanop", "#chan", ListRemainder(ANYSTR, min_length=1)],
                )
                final_param = message.params[2]
                self.assertEqual(final_param[0], "+")
                enabled_modes = list(final_param[1:])
                break

        self.assertLessEqual({"i", "n", "t"}, set(enabled_modes))

        # remove all the modes listed by RPL_CHANNELMODEIS
        self.sendLine("chanop", f"MODE #chan -{''.join(enabled_modes)}")
        response = self.getMessage("chanop")
        self.assertMessageMatch(response, command="MODE", params=["#chan", ANYSTR])
        self.assertEqual(response.params[1][0], "-")
        self.assertEqual(set(response.params[1][1:]), set(enabled_modes))

        self.sendLine("chanop", "MODE #chan")
        messages = self.getMessages("chanop")
        self.assertLessEqual(expected_numerics, {msg.command for msg in messages})
        # all modes have been disabled; the correct representation of this is `+`
        for message in messages:
            if message.command == RPL_CHANNELMODEIS:
                self.assertMessageMatch(
                    message,
                    command=RPL_CHANNELMODEIS,
                    params=["chanop", "#chan", "+"],
                )
