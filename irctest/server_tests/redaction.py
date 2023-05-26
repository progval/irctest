"""
`IRCv3 draft message redaction <https://github.com/progval/ircv3-specifications/blob/redaction/extensions/message-redaction.md>`_
"""

from irctest import cases
from irctest.patma import ANYDICT, ANYSTR, StrRe

CAPABILITIES = [
    "message-tags",
    "echo-message",
    "labeled-response",
    "draft/message-redaction",
]


@cases.mark_specifications("IRCv3")
@cases.mark_capabilities(*CAPABILITIES)
class RedactTestCase(cases.BaseServerTestCase):
    def _setupRedactTest(self, redacteeId, redacteeNick):
        self.connectClient("chanop", capabilities=CAPABILITIES, skip_if_cap_nak=True)
        self.sendLine(1, "JOIN #chan")
        self.connectClient("user", capabilities=CAPABILITIES, skip_if_cap_nak=True)
        self.sendLine(2, "JOIN #chan")
        self.getMessages(2)  # synchronize
        self.getMessages(1)

        self.sendLine(redacteeId, "@label=1234 PRIVMSG #chan :hello there")
        echo = self.getMessage(redacteeId)
        self.assertMessageMatch(
            echo,
            tags={"label": "1234", "msgid": StrRe("[^ ]+"), **ANYDICT},
            prefix=StrRe(redacteeNick + "!.*"),
            command="PRIVMSG",
            params=["#chan", "hello there"],
        )
        msgid = echo.tags["msgid"]

        self.assertMessageMatch(
            self.getMessage(3 - redacteeId),
            tags={"msgid": msgid, **ANYDICT},
            prefix=StrRe(redacteeNick + "!.*"),
            command="PRIVMSG",
            params=["#chan", "hello there"],
        )

        return msgid

    def testRelayOpSelfRedact(self):
        """Channel op writes a message and redacts it themselves."""
        msgid = self._setupRedactTest(redacteeId=1, redacteeNick="chanop")

        self.sendLine(1, f"REDACT #chan {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "oops"],
        )

        self.assertMessageMatch(
            self.getMessage(2),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "oops"],
        )

    def testRelayOpRedact(self):
        """User writes a message and channel op redacts it."""
        msgid = self._setupRedactTest(
            redacteeId=2,
            redacteeNick="user",
        )

        self.sendLine(1, f"REDACT #chan {msgid} :spam")
        self.assertMessageMatch(
            self.getMessage(1),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "spam"],
        )

        self.assertMessageMatch(
            self.getMessage(2),
            prefix=StrRe("chanop!.*"),
            command="REDACT",
            params=["#chan", msgid, "spam"],
        )

    def testRelayUserSelfRedact(self):
        """User writes a message and redacts it themselves.

        Servers may either accept or reject this."""
        msgid = self._setupRedactTest(redacteeId=2, redacteeNick="user")

        self.sendLine(2, f"REDACT #chan {msgid} :oops")

        msg = self.getMessage(2)
        if msg.command == "REDACT":
            self.assertMessageMatch(
                msg,
                prefix=StrRe("user!.*"),
                command="REDACT",
                params=["#chan", msgid, "oops"],
            )

            self.assertMessageMatch(
                self.getMessage(1),
                prefix=StrRe("user!.*"),
                command="REDACT",
                params=["#chan", msgid, "oops"],
            )
        else:
            self.assertMessageMatch(
                msg,
                command="FAIL",
                params=["REDACT", "REDACT_FORBIDDEN", "#chan", msgid, ANYSTR],
            )

            self.assertEqual(self.getMessages(1), [])

    def testRejectRedactOtherUser(self):
        """Channel op writes a message and a user attempts to redact it."""
        msgid = self._setupRedactTest(redacteeId=1, redacteeNick="chanop")

        self.sendLine(2, f"REDACT #chan {msgid} :oops")
        self.assertMessageMatch(
            self.getMessage(2),
            command="FAIL",
            params=["REDACT", "REDACT_FORBIDDEN", "#chan", msgid, ANYSTR],
        )

        self.assertEqual(self.getMessages(1), [])
