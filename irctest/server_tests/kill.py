"""
The KILL command  (`Modern <https://modern.ircdocs.horse/#kill-message>`__)
"""


from irctest import cases
from irctest.numerics import ERR_NOPRIVILEGES, RPL_YOUREOPER


class KillTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    def testKill(self):
        self.connectClient("ircop", name="ircop")
        self.connectClient("alice", name="alice")
        self.connectClient("bob", name="bob")

        self.sendLine("ircop", "OPER operuser operpassword")
        self.assertIn(
            RPL_YOUREOPER,
            [m.command for m in self.getMessages("ircop")],
            fail_msg="OPER failed",
        )

        self.sendLine("alice", "KILL bob :no reason")
        self.assertIn(
            ERR_NOPRIVILEGES,
            [m.command for m in self.getMessages("alice")],
            fail_msg="unprivileged KILL not rejected",
        )
        # bob is not killed
        self.getMessages("bob")

        self.sendLine("alice", "KILL alice :no reason")
        self.assertIn(
            ERR_NOPRIVILEGES,
            [m.command for m in self.getMessages("alice")],
            fail_msg="unprivileged KILL not rejected",
        )
        # alice is not killed
        self.getMessages("alice")

        # privileged KILL should succeed
        self.sendLine("ircop", "KILL alice :no reason")
        self.getMessages("ircop")
        self.assertDisconnected("alice")

        self.sendLine("ircop", "KILL bob")
        self.getMessages("ircop")
        self.assertDisconnected("bob")

    @cases.mark_specifications("Ergo")
    def testKillOneArgument(self):
        self.connectClient("ircop", name="ircop")
        self.connectClient("alice", name="alice")

        self.sendLine("ircop", "OPER operuser operpassword")
        self.assertIn(
            RPL_YOUREOPER,
            [m.command for m in self.getMessages("ircop")],
            fail_msg="OPER failed",
        )

        # 1-argument kill command, accepted by Ergo and some implementations
        self.sendLine("ircop", "KILL alice")
        self.getMessages("ircop")
        self.assertDisconnected("alice")
