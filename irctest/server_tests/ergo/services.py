"""
`Ergo <https://ergo.chat/>`-specific tests of NickServ.
"""

from irctest import cases
from irctest.numerics import RPL_YOUREOPER


class NickservTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def test_saregister(self):
        self.connectClient("root", name="root")
        self.sendLine("root", "OPER operuser operpassword")
        self.assertIn(RPL_YOUREOPER, {msg.command for msg in self.getMessages("root")})

        self.sendLine(
            "root",
            "PRIVMSG NickServ :SAREGISTER saregister_test saregistertestpassphrase",
        )
        self.getMessages("root")

        # test that the account was registered
        self.connectClient(
            name="saregister_test",
            nick="saregister_test",
            capabilities=["sasl"],
            account="saregister_test",
            password="saregistertestpassphrase",
        )
