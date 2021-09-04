from irctest import cases
from irctest.numerics import ERR_BANNEDFROMCHAN


class BanMode(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testBan(self):
        """Basic ban operation"""
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.connectClient(
            "Bar", name="bar", capabilities=["echo-message"], skip_if_cap_nak=True
        )
        self.getMessages("bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_BANNEDFROMCHAN)

        self.sendLine("chanop", "MODE #chan -b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")

    @cases.mark_specifications("Ergo")
    def testCaseInsensitive(self):
        """Some clients allow unsetting modes if their argument matches
        up to normalization"""
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +b BAR!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.connectClient("Bar", name="bar", capabilities=["echo-message"])
        self.getMessages("bar")
        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command=ERR_BANNEDFROMCHAN)

        self.sendLine("chanop", "MODE #chan -b bar!*@*")
        self.assertMessageMatch(self.getMessage("chanop"), command="MODE")

        self.sendLine("bar", "JOIN #chan")
        self.assertMessageMatch(self.getMessage("bar"), command="JOIN")
