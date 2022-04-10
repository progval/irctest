"""
Channel key (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.3.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.3>`__,
`Modern <https://modern.ircdocs.horse/#key-channel-mode>`__)
"""

import pytest

from irctest import cases
from irctest.numerics import (
    ERR_BADCHANNELKEY,
    ERR_INVALIDKEY,
    ERR_INVALIDMODEPARAM,
    ERR_UNKNOWNERROR,
)
from irctest.patma import ANYSTR


class KeyTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testKeyNormal(self):
        self.connectClient("bar")
        self.joinChannel(1, "#chan")
        self.sendLine(1, "MODE #chan +k beer")
        self.getMessages(1)

        self.connectClient("qux")
        self.getMessages(2)
        self.sendLine(2, "JOIN #chan")
        reply = self.getMessages(2)
        self.assertNotIn("JOIN", {msg.command for msg in reply})
        self.assertIn(ERR_BADCHANNELKEY, {msg.command for msg in reply})

        self.sendLine(2, "JOIN #chan beer")
        reply = self.getMessages(2)
        self.assertMessageMatch(reply[0], command="JOIN", params=["#chan"])

    @pytest.mark.parametrize(
        "key",
        ["passphrase with spaces", "long" * 100, ""],
        ids=["spaces", "long", "empty"],
    )
    @cases.mark_specifications("RFC2812", "Modern")
    def testKeyValidation(self, key):
        """
          key        =  1*23( %x01-05 / %x07-08 / %x0C / %x0E-1F / %x21-7F )
                  ; any 7-bit US_ASCII character,
                  ; except NUL, CR, LF, FF, h/v TABs, and " "
        -- https://tools.ietf.org/html/rfc2812#page-8

        "Servers may validate the value (eg. to forbid spaces, as they make it harder
        to use the key in `JOIN` messages). If the value is invalid, they SHOULD
        return [`ERR_INVALIDMODEPARAM`](#errinvalidmodeparam-696).
        However, clients MUST be able to handle any of the following:

        * [`ERR_INVALIDMODEPARAM`](#errinvalidmodeparam-696)
        * [`ERR_INVALIDKEY`](#errinvalidkey-525)
        * `MODE` echoed with a different key (eg. truncated or stripped of invalid
          characters)
        * the key changed ignored, and no `MODE` echoed if no other mode change
          was valid.
        "
        -- https://modern.ircdocs.horse/#key-channel-mode
        -- https://github.com/ircdocs/modern-irc/pull/111
        """
        self.connectClient("bar")
        self.joinChannel(1, "#chan")
        self.sendLine(1, f"MODE #chan +k :{key}")

        # The spec requires no space; but doesn't say what to do
        # if there is one.
        # Let's check the various alternatives

        replies = self.getMessages(1)
        self.assertNotIn(
            ERR_UNKNOWNERROR,
            {msg.command for msg in replies},
            fail_msg="Sending an invalid key caused an "
            "ERR_UNKNOWNERROR instead of being handled explicitly "
            "(eg. ERR_INVALIDMODEPARAM or truncation): {msg}",
        )

        commands = {msg.command for msg in replies}
        if {ERR_INVALIDMODEPARAM, ERR_INVALIDKEY} & commands:
            # First option: ERR_INVALIDMODEPARAM (eg. Ergo) or ERR_INVALIDKEY
            # (eg. ircu2)
            if ERR_INVALIDMODEPARAM in commands:
                command = [
                    msg for msg in replies if msg.command == ERR_INVALIDMODEPARAM
                ]
                self.assertEqual(len(command), 1, command)
                self.assertMessageMatch(
                    command[0],
                    command=ERR_INVALIDMODEPARAM,
                    params=["bar", "#chan", "k", "*", ANYSTR],
                )
            return

        if not replies:
            # MODE was ignored entirely
            self.connectClient("foo")
            self.sendLine(2, "JOIN #chan")
            self.assertMessageMatch(
                self.getMessage(2), command="JOIN", params=["#chan"]
            )
            return

        # Second and third options: truncating the key (eg. UnrealIRCd)
        # or replacing spaces (eg. Charybdis)
        mode_commands = [msg for msg in replies if msg.command == "MODE"]
        self.assertGreaterEqual(
            len(mode_commands),
            1,
            fail_msg="Sending an invalid key (with a space) triggered "
            "neither ERR_UNKNOWNERROR, ERR_INVALIDMODEPARAM, ERR_INVALIDKEY, "
            " or a MODE. Only these: {}",
            extra_format=(replies,),
        )
        self.assertLessEqual(
            len(mode_commands),
            1,
            fail_msg="Sending an invalid key (with a space) triggered "
            "multiple MODE responses: {}",
            extra_format=(replies,),
        )

        mode_command = mode_commands[0]
        if mode_command.params == ["#chan", "+k", "passphrase"]:
            key = "passphrase"
        elif mode_command.params == ["#chan", "+k", "passphrasewithspaces"]:
            key = "passphrasewithspaces"
        elif mode_command.params[2].startswith("longlonglong"):
            key = mode_command.params[2]
            assert mode_command.params == ["#chan", "+k", key]
        elif mode_command.params == ["#chan", "+k", "passphrase with spaces"]:
            raise self.failureException("Invalid key (with a space) was not rejected.")

        self.connectClient("foo")
        self.sendLine(2, f"JOIN #chan {key}")
        self.assertMessageMatch(self.getMessage(2), command="JOIN", params=["#chan"])
