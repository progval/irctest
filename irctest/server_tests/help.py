"""
The HELP and HELPOP command (`Modern <https://modern.ircdocs.horse/#help-message>`__)
"""

import functools
import re

import pytest

from irctest import cases, runner
from irctest.numerics import (
    ERR_HELPNOTFOUND,
    ERR_UNKNOWNCOMMAND,
    RPL_ENDOFHELP,
    RPL_HELPSTART,
    RPL_HELPTXT,
)
from irctest.patma import ANYSTR, StrRe


def with_xfails(f):
    @functools.wraps(f)
    def newf(self, command, *args, **kwargs):
        if command == "HELP" and self.controller.software_name == "Bahamut":
            raise runner.NotImplementedByController(
                "fail because Bahamut forwards /HELP to HelpServ (but not /HELPOP)"
            )

        if self.controller.software_name in ("irc2", "ircu2", "ngIRCd"):
            raise runner.NotImplementedByController(
                "numerics in reply to /HELP and /HELPOP (uses NOTICE instead)"
            )

        if self.controller.software_name == "UnrealIRCd":
            raise runner.NotImplementedByController(
                "fails because Unreal uses custom numerics "
                "https://github.com/unrealircd/unrealircd/pull/184"
            )

        return f(self, command, *args, **kwargs)

    return newf


class HelpTestCase(cases.BaseServerTestCase):
    def _assertValidHelp(self, messages, subject):
        if subject != ANYSTR:
            subject = StrRe("(?i)" + re.escape(subject))

        self.assertMessageMatch(
            messages[0],
            command=RPL_HELPSTART,
            params=["nick", subject, ANYSTR],
            fail_msg=f"Expected {RPL_HELPSTART} (RPL_HELPSTART), got: {{msg}}",
        )

        self.assertMessageMatch(
            messages[-1],
            command=RPL_ENDOFHELP,
            params=["nick", subject, ANYSTR],
            fail_msg=f"Expected {RPL_ENDOFHELP} (RPL_ENDOFHELP), got: {{msg}}",
        )

        for i in range(1, len(messages) - 1):
            self.assertMessageMatch(
                messages[i],
                command=RPL_HELPTXT,
                params=["nick", subject, ANYSTR],
                fail_msg=f"Expected {RPL_HELPTXT} (RPL_HELPTXT), got: {{msg}}",
            )

    @pytest.mark.parametrize("command", ["HELP", "HELPOP"])
    @cases.mark_specifications("Modern")
    @with_xfails
    def testHelpNoArg(self, command):
        self.connectClient("nick")
        self.sendLine(1, f"{command}")

        messages = self.getMessages(1)

        if messages[0].command == ERR_UNKNOWNCOMMAND:
            raise runner.OptionalCommandNotSupported(command)

        self._assertValidHelp(messages, ANYSTR)

    @pytest.mark.parametrize("command", ["HELP", "HELPOP"])
    @cases.mark_specifications("Modern")
    @with_xfails
    def testHelpPrivmsg(self, command):
        self.connectClient("nick")
        self.sendLine(1, f"{command} PRIVMSG")
        messages = self.getMessages(1)

        if messages[0].command == ERR_UNKNOWNCOMMAND:
            raise runner.OptionalCommandNotSupported(command)

        self._assertValidHelp(messages, "PRIVMSG")

    @pytest.mark.parametrize("command", ["HELP", "HELPOP"])
    @cases.mark_specifications("Modern")
    @with_xfails
    def testHelpUnknownSubject(self, command):
        self.connectClient("nick")
        self.sendLine(1, f"{command} THISISNOTACOMMAND")
        messages = self.getMessages(1)

        if messages[0].command == ERR_UNKNOWNCOMMAND:
            raise runner.OptionalCommandNotSupported(command)

        if messages[0].command == ERR_HELPNOTFOUND:
            # Inspircd, Hybrid et al
            self.assertEqual(len(messages), 1)
            self.assertMessageMatch(
                messages[0],
                command=ERR_HELPNOTFOUND,
                params=[
                    "nick",
                    StrRe(
                        "(?i)THISISNOTACOMMAND"
                    ),  # case-insensitive, for Hybrid and Plexus4 (but not Chary et al)
                    ANYSTR,
                ],
            )
        else:
            # Unrealircd
            self._assertValidHelp(messages, ANYSTR)
