import math
import time

from irctest import cases, runner
from irctest.irc_utils.junkdrawer import ircv3_timestamp_to_unixtime
from irctest.numerics import (
    ERR_BADCHANNELKEY,
    ERR_BANNEDFROMCHAN,
    ERR_CANNOTSENDTOCHAN,
    ERR_CHANOPRIVSNEEDED,
    ERR_INVALIDKEY,
    ERR_INVALIDMODEPARAM,
    ERR_UNKNOWNERROR,
    RPL_NAMREPLY,
)
from irctest.patma import ANYLIST, StrRe

MODERN_CAPS = [
    "server-time",
    "message-tags",
    "batch",
    "labeled-response",
    "echo-message",
    "account-tag",
]


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

    @cases.mark_specifications("RFC2812", "Modern")
    def testKeyValidation(self):
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
        self.sendLine(1, "MODE #chan +k :passphrase with spaces")

        # The spec requires no space; but doesn't say what to do
        # if there is one.
        # Let's check the various alternatives

        replies = self.getMessages(1)
        self.assertNotIn(
            ERR_UNKNOWNERROR,
            {msg.command for msg in replies},
            fail_msg="Sending an invalid key (with a space) caused an "
            "ERR_UNKNOWNERROR instead of being handled explicitly "
            "(eg. ERR_INVALIDMODEPARAM or truncation): {msg}",
        )

        if {ERR_INVALIDMODEPARAM, ERR_INVALIDKEY} & {msg.command for msg in replies}:
            # First option: ERR_INVALIDMODEPARAM (eg. Ergo) or ERR_INVALIDKEY
            # (eg. ircu2)
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
        elif mode_command.params == ["#chan", "+k", "passphrase with spaces"]:
            raise self.failureException("Invalid key (with a space) was not rejected.")

        self.connectClient("foo")
        self.sendLine(2, f"JOIN #chan {key}")
        self.assertMessageMatch(self.getMessage(2), command="JOIN", params=["#chan"])


class AuditoriumTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testAuditorium(self):
        self.connectClient("bar", name="bar", capabilities=MODERN_CAPS)
        self.joinChannel("bar", "#auditorium")
        self.getMessages("bar")
        self.sendLine("bar", "MODE #auditorium +u")
        modelines = [msg for msg in self.getMessages("bar") if msg.command == "MODE"]
        self.assertEqual(len(modelines), 1)
        self.assertMessageMatch(modelines[0], params=["#auditorium", "+u"])

        self.connectClient("guest1", name="guest1", capabilities=MODERN_CAPS)
        self.joinChannel("guest1", "#auditorium")
        self.getMessages("guest1")
        # chanop should get a JOIN message
        join_msgs = [msg for msg in self.getMessages("bar") if msg.command == "JOIN"]
        self.assertEqual(len(join_msgs), 1)
        self.assertMessageMatch(join_msgs[0], nick="guest1", params=["#auditorium"])

        self.connectClient("guest2", name="guest2", capabilities=MODERN_CAPS)
        self.joinChannel("guest2", "#auditorium")
        self.getMessages("guest2")
        # chanop should get a JOIN message
        join_msgs = [msg for msg in self.getMessages("bar") if msg.command == "JOIN"]
        self.assertEqual(len(join_msgs), 1)
        join_msg = join_msgs[0]
        self.assertMessageMatch(join_msg, nick="guest2", params=["#auditorium"])
        # oragono/oragono#1642 ; msgid should be populated,
        # and the time tag should be sane
        self.assertTrue(join_msg.tags.get("msgid"))
        self.assertLessEqual(
            math.fabs(time.time() - ircv3_timestamp_to_unixtime(join_msg.tags["time"])),
            60.0,
        )
        # fellow unvoiced participant should not
        unvoiced_join_msgs = [
            msg for msg in self.getMessages("guest1") if msg.command == "JOIN"
        ]
        self.assertEqual(len(unvoiced_join_msgs), 0)

        self.connectClient("guest3", name="guest3", capabilities=MODERN_CAPS)
        self.joinChannel("guest3", "#auditorium")
        self.getMessages("guest3")

        self.sendLine("bar", "PRIVMSG #auditorium hi")
        echo_message = [
            msg for msg in self.getMessages("bar") if msg.command == "PRIVMSG"
        ][0]
        self.assertEqual(echo_message, self.getMessages("guest1")[0])
        self.assertEqual(echo_message, self.getMessages("guest2")[0])
        self.assertEqual(echo_message, self.getMessages("guest3")[0])

        # unvoiced users can speak
        self.sendLine("guest1", "PRIVMSG #auditorium :hi you")
        echo_message = [
            msg for msg in self.getMessages("guest1") if msg.command == "PRIVMSG"
        ][0]
        self.assertEqual(self.getMessages("bar"), [echo_message])
        self.assertEqual(self.getMessages("guest2"), [echo_message])
        self.assertEqual(self.getMessages("guest3"), [echo_message])

        def names(client):
            self.sendLine(client, "NAMES #auditorium")
            result = set()
            for msg in self.getMessages(client):
                if msg.command == RPL_NAMREPLY:
                    result.update(msg.params[-1].split())
            return result

        self.assertEqual(names("bar"), {"@bar", "guest1", "guest2", "guest3"})
        self.assertEqual(names("guest1"), {"@bar"})
        self.assertEqual(names("guest2"), {"@bar"})
        self.assertEqual(names("guest3"), {"@bar"})

        self.sendLine("bar", "MODE #auditorium +v guest1")
        modeLine = [msg for msg in self.getMessages("bar") if msg.command == "MODE"][0]
        self.assertEqual(self.getMessages("guest1"), [modeLine])
        self.assertEqual(self.getMessages("guest2"), [modeLine])
        self.assertEqual(self.getMessages("guest3"), [modeLine])
        self.assertEqual(names("bar"), {"@bar", "+guest1", "guest2", "guest3"})
        self.assertEqual(names("guest2"), {"@bar", "+guest1"})
        self.assertEqual(names("guest3"), {"@bar", "+guest1"})

        self.sendLine("guest1", "PART #auditorium")
        part = [msg for msg in self.getMessages("guest1") if msg.command == "PART"][0]
        # everyone should see voiced PART
        self.assertEqual(self.getMessages("bar")[0], part)
        self.assertEqual(self.getMessages("guest2")[0], part)
        self.assertEqual(self.getMessages("guest3")[0], part)

        self.joinChannel("guest1", "#auditorium")
        self.getMessages("guest1")
        self.getMessages("bar")

        self.sendLine("guest2", "PART #auditorium")
        part = [msg for msg in self.getMessages("guest2") if msg.command == "PART"][0]
        self.assertEqual(self.getMessages("bar"), [part])
        # part should be hidden from unvoiced participants
        self.assertEqual(self.getMessages("guest1"), [])
        self.assertEqual(self.getMessages("guest3"), [])

        self.sendLine("guest3", "QUIT")
        self.assertDisconnected("guest3")
        # quit should be hidden from unvoiced participants
        self.assertEqual(
            len([msg for msg in self.getMessages("bar") if msg.command == "QUIT"]), 1
        )
        self.assertEqual(
            len([msg for msg in self.getMessages("guest1") if msg.command == "QUIT"]), 0
        )


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


class ModeratedMode(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC2812")
    def testModeratedMode(self):
        # test the +m channel mode
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +m")
        replies = self.getMessages("chanop")
        modeLines = [line for line in replies if line.command == "MODE"]
        self.assertMessageMatch(modeLines[0], command="MODE", params=["#chan", "+m"])

        self.connectClient("baz", name="baz")
        self.joinChannel("baz", "#chan")
        self.getMessages("chanop")
        # this message should be suppressed completely by +m
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        replies = self.getMessages("baz")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(ERR_CANNOTSENDTOCHAN, reply_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # grant +v, user should be able to send messages
        self.sendLine("chanop", "MODE #chan +v baz")
        self.getMessages("chanop")
        self.getMessages("baz")
        self.sendLine("baz", "PRIVMSG #chan :hi again from baz")
        self.getMessages("baz")
        relays = self.getMessages("chanop")
        relay = relays[0]
        self.assertMessageMatch(
            relay, command="PRIVMSG", params=["#chan", "hi again from baz"]
        )


@cases.mark_services
class RegisteredOnlySpeakMode(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testRegisteredOnlySpeakMode(self):
        self.controller.registerUser(self, "evan", "sesame")

        # test the +M (only registered users and ops can speak) channel mode
        self.connectClient("chanop", name="chanop")
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +M")
        replies = self.getMessages("chanop")
        modeLines = [line for line in replies if line.command == "MODE"]
        self.assertMessageMatch(modeLines[0], command="MODE", params=["#chan", "+M"])

        self.connectClient("baz", name="baz")
        self.joinChannel("baz", "#chan")
        self.getMessages("chanop")
        # this message should be suppressed completely by +M
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        replies = self.getMessages("baz")
        reply_cmds = {reply.command for reply in replies}
        self.assertIn(ERR_CANNOTSENDTOCHAN, reply_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # +v exempts users from the registration requirement:
        self.sendLine("chanop", "MODE #chan +v baz")
        self.getMessages("chanop")
        self.getMessages("baz")
        self.sendLine("baz", "PRIVMSG #chan :hi again from baz")
        replies = self.getMessages("baz")
        # baz should not receive an error (or an echo)
        self.assertEqual(replies, [])
        replies = self.getMessages("chanop")
        self.assertMessageMatch(
            replies[0], command="PRIVMSG", params=["#chan", "hi again from baz"]
        )

        self.connectClient(
            "evan",
            name="evan",
            account="evan",
            password="sesame",
            capabilities=["sasl"],
        )
        self.joinChannel("evan", "#chan")
        self.getMessages("baz")
        self.sendLine("evan", "PRIVMSG #chan :hi from evan")
        replies = self.getMessages("evan")
        # evan should not receive an error (or an echo)
        self.assertEqual(replies, [])
        replies = self.getMessages("baz")
        self.assertMessageMatch(
            replies[0], command="PRIVMSG", params=["#chan", "hi from evan"]
        )


class OpModerated(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def testOpModerated(self):
        # test the +U channel mode
        self.connectClient("chanop", name="chanop", capabilities=MODERN_CAPS)
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", "MODE #chan +U")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("baz", name="baz", capabilities=MODERN_CAPS)
        self.joinChannel("baz", "#chan")
        self.sendLine("baz", "PRIVMSG #chan :hi from baz")
        echo = self.getMessages("baz")[0]
        self.assertMessageMatch(
            echo, command="PRIVMSG", params=["#chan", "hi from baz"]
        )
        self.assertEqual(
            [msg for msg in self.getMessages("chanop") if msg.command == "PRIVMSG"],
            [echo],
        )

        self.connectClient("qux", name="qux", capabilities=MODERN_CAPS)
        self.joinChannel("qux", "#chan")
        self.sendLine("qux", "PRIVMSG #chan :hi from qux")
        echo = self.getMessages("qux")[0]
        self.assertMessageMatch(
            echo, command="PRIVMSG", params=["#chan", "hi from qux"]
        )
        # message is relayed to chanop but not to unprivileged
        self.assertEqual(
            [msg for msg in self.getMessages("chanop") if msg.command == "PRIVMSG"],
            [echo],
        )
        self.assertEqual(
            [msg for msg in self.getMessages("baz") if msg.command == "PRIVMSG"], []
        )

        self.sendLine("chanop", "MODE #chan +v qux")
        self.getMessages("chanop")
        self.sendLine("qux", "PRIVMSG #chan :hi again from qux")
        echo = [msg for msg in self.getMessages("qux") if msg.command == "PRIVMSG"][0]
        self.assertMessageMatch(
            echo, command="PRIVMSG", params=["#chan", "hi again from qux"]
        )
        self.assertEqual(
            [msg for msg in self.getMessages("chanop") if msg.command == "PRIVMSG"],
            [echo],
        )
        self.assertEqual(
            [msg for msg in self.getMessages("baz") if msg.command == "PRIVMSG"], [echo]
        )


class MuteExtban(cases.BaseServerTestCase):
    """https://defs.ircdocs.horse/defs/isupport.html#extban

    It magically guesses what char the IRCd uses for mutes."""

    def char(self):
        if self.controller.extban_mute_char is None:
            raise runner.ExtbanNotSupported("", "mute")
        else:
            return self.controller.extban_mute_char

    @cases.mark_specifications("Ergo")
    def testISupport(self):
        self.connectClient(1)  # Fetches ISUPPORT
        isupport = self.server_support
        token = isupport["EXTBAN"]
        prefix, comma, types = token.partition(",")
        self.assertIn(self.char(), types, f"Missing '{self.char()}' in ISUPPORT EXTBAN")
        self.assertEqual(prefix, "")
        self.assertEqual(comma, ",")

    @cases.mark_specifications("ircdocs")
    def testMuteExtban(self):
        """Basic usage of mute"""
        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")
        if self.char() not in types:
            raise runner.ExtbanNotSupported(self.char(), "mute")

        clients = ("chanop", "bar")

        # Mute "bar"
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:bar!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("bar", name="bar", capabilities=["echo-message"])
        self.joinChannel("bar", "#chan")

        for client in clients:
            self.getMessages(client)

        # "bar" sees the MODE too
        self.sendLine("bar", "MODE #chan +b")
        self.assertMessageMatch(
            self.getMessage("bar"),
            command="367",
            params=[
                "bar",
                "#chan",
                f"{prefix}{self.char()}:bar!*@*",
                StrRe("chanop(!.*)?"),
                *ANYLIST,
            ],
        )
        self.getMessages("bar")

        # "bar" talks: rejected
        self.sendLine("bar", "PRIVMSG #chan :hi from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # remove mute on "bar" with -b
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan -b {prefix}{self.char()}:bar!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # "bar" can now talk
        self.sendLine("bar", "PRIVMSG #chan :hi again from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )

    @cases.mark_specifications("ircdocs")
    def testMuteExtbanVoiced(self):
        """Checks +v overrides the mute"""
        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")
        if self.char() not in types:
            raise runner.ExtbanNotSupported(self.char(), "mute")

        clients = ("chanop", "qux")

        # Mute "qux"
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:qux!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient(
            "qux", name="qux", ident="evan", capabilities=["echo-message"]
        )
        self.joinChannel("qux", "#chan")

        for client in clients:
            self.getMessages(client)

        # "qux" talks: rejected
        self.sendLine("qux", "PRIVMSG #chan :hi from qux")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        for client in clients:
            self.getMessages(client)

        # +v grants an exemption to +b
        self.sendLine("chanop", "MODE #chan +v qux")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # so "qux" can now talk
        self.sendLine("qux", "PRIVMSG #chan :hi again from qux")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )

    @cases.mark_specifications("ircdocs")
    def testMuteExtbanExempt(self):
        """Checks +e overrides the mute

        <https://defs.ircdocs.horse/defs/chanmodes.html#e-ban-exception>"""
        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")
        if self.char() not in types:
            raise runner.ExtbanNotSupported(self.char(), "mute")
        if "e" not in self.server_support["CHANMODES"]:
            raise runner.ChannelModeNotSupported(self.char(), "mute")

        clients = ("chanop", "qux")

        # Mute "qux"
        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:qux!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient(
            "qux", name="qux", ident="evan", capabilities=["echo-message"]
        )
        self.joinChannel("qux", "#chan")

        for client in clients:
            self.getMessages(client)

        # "qux" talks: rejected
        self.sendLine("qux", "PRIVMSG #chan :hi from qux")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        for client in clients:
            self.getMessages(client)

        # +e grants an exemption to +b
        self.sendLine("chanop", f"MODE #chan +e {prefix}{self.char()}:*!~evan@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.getMessages("qux")

        # so "qux" can now talk
        self.sendLine("qux", "PRIVMSG #chan :thanks for mute-excepting me")
        replies = self.getMessages("qux")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )

    @cases.mark_specifications("Ergo")
    def testCapitalization(self):
        """
        Regression test for oragono #1370: mutes not correctly enforced against
        users with capital letters in their NUH

        For consistency with regular -b, which allows unsetting up to
        normalization
        """
        clients = ("chanop", "bar")

        self.connectClient("chanop", name="chanop")

        isupport = self.server_support
        token = isupport.get("EXTBAN", "")
        prefix, comma, types = token.partition(",")

        self.joinChannel("chanop", "#chan")
        self.getMessages("chanop")
        self.sendLine("chanop", f"MODE #chan +b {prefix}{self.char()}:BAR!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        self.connectClient("Bar", name="bar", capabilities=["echo-message"])
        self.joinChannel("bar", "#chan")

        for client in clients:
            self.getMessages(client)

        self.sendLine("bar", "PRIVMSG #chan :hi from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertNotIn("PRIVMSG", replies_cmds)
        self.assertIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(self.getMessages("chanop"), [])

        # remove mute with -b
        self.sendLine("chanop", f"MODE #chan -b {prefix}{self.char()}:bar!*@*")
        replies = {msg.command for msg in self.getMessages("chanop")}
        self.assertIn("MODE", replies)
        self.assertNotIn(ERR_CHANOPRIVSNEEDED, replies)

        # "bar" can talk again
        self.sendLine("bar", "PRIVMSG #chan :hi again from bar")
        replies = self.getMessages("bar")
        replies_cmds = {msg.command for msg in replies}
        self.assertIn("PRIVMSG", replies_cmds)
        self.assertNotIn(ERR_CANNOTSENDTOCHAN, replies_cmds)
        self.assertEqual(
            self.getMessages("chanop"),
            [msg for msg in replies if msg.command == "PRIVMSG"],
        )
