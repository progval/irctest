from irctest import cases
from irctest.irc_utils.sasl import sasl_plain_blob
from irctest.numerics import RPL_LOGGEDIN, RPL_SASLSUCCESS, RPL_YOUREOPER


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
        self.addClient("saregister_test")
        self.sendLine("saregister_test", "CAP REQ sasl")
        self.sendLine("saregister_test", "NICK asdf")
        self.sendLine("saregister_test", "USER u s e r")
        self.sendLine("saregister_test", "AUTHENTICATE PLAIN")
        self.sendLine(
            "saregister_test",
            sasl_plain_blob("saregister_test", "saregistertestpassphrase"),
        )
        self.sendLine("saregister_test", "CAP END")
        replies = {msg.command for msg in self.getMessages("saregister_test")}
        self.assertIn(RPL_LOGGEDIN, replies)
        self.assertIn(RPL_SASLSUCCESS, replies)
