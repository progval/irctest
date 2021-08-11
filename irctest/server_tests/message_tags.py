"""
https://ircv3.net/specs/extensions/message-tags.html
"""

import pytest

from irctest import cases
from irctest.irc_utils.message_parser import parse_message
from irctest.numerics import ERR_INPUTTOOLONG
from irctest.patma import ANYDICT, ANYSTR, StrRe


class MessageTagsTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @pytest.mark.arbitrary_client_tags
    @cases.mark_capabilities("message-tags")
    def testBasic(self):
        def getAllMessages():
            for name in ["alice", "bob", "carol", "dave"]:
                self.getMessages(name)

        def assertNoTags(line):
            # tags start with '@', without tags we start with the prefix,
            # which begins with ':'
            self.assertEqual(line[0], ":")
            msg = parse_message(line)
            self.assertEqual(msg.tags, {})
            return msg

        self.connectClient(
            "alice", name="alice", capabilities=["message-tags"], skip_if_cap_nak=True
        )
        self.joinChannel("alice", "#test")
        self.connectClient(
            "bob", name="bob", capabilities=["message-tags", "echo-message"]
        )
        self.joinChannel("bob", "#test")
        self.connectClient("carol", name="carol")
        self.joinChannel("carol", "#test")
        self.connectClient("dave", name="dave", capabilities=["server-time"])
        self.joinChannel("dave", "#test")
        getAllMessages()

        self.sendLine("alice", "@+baz=bat;fizz=buzz PRIVMSG #test hi")
        self.getMessages("alice")
        bob_msg = self.getMessage("bob")
        carol_line = self.getMessage("carol", raw=True)
        self.assertMessageMatch(
            bob_msg,
            command="PRIVMSG",
            params=["#test", "hi"],
            tags={"+baz": "bat", "msgid": ANYSTR, **ANYDICT},
        )
        # should not relay a non-client-only tag
        self.assertNotIn("fizz", bob_msg.tags)
        # carol MUST NOT receive tags
        carol_msg = assertNoTags(carol_line)
        self.assertMessageMatch(carol_msg, command="PRIVMSG", params=["#test", "hi"])
        # dave SHOULD receive server-time tag
        dave_msg = self.getMessage("dave")
        self.assertMessageMatch(
            dave_msg,
            command="PRIVMSG",
            params=["#test", "hi"],
            tags={"time": ANYSTR, **ANYDICT},
        )
        # dave MUST NOT receive client-only tags
        self.assertNotIn("+baz", dave_msg.tags)
        getAllMessages()

        self.sendLine("bob", "@+bat=baz;+fizz=buzz PRIVMSG #test :hi yourself")
        bob_msg = self.getMessage("bob")  # bob has echo-message
        alice_msg = self.getMessage("alice")
        carol_line = self.getMessage("carol", raw=True)
        carol_msg = assertNoTags(carol_line)
        for msg in [alice_msg, bob_msg]:
            self.assertMessageMatch(
                msg,
                command="PRIVMSG",
                params=["#test", "hi yourself"],
                tags={"+bat": "baz", "+fizz": "buzz", "msgid": ANYSTR, **ANYDICT},
            )
        self.assertMessageMatch(
            carol_msg,
            command="PRIVMSG",
            params=["#test", "hi yourself"],
        )
        self.assertEqual(alice_msg.tags["msgid"], bob_msg.tags["msgid"])
        getAllMessages()

        # test TAGMSG and basic escaping
        self.sendLine("bob", r"@+buzz=fizz\:buzz;cat=dog;+steel=wootz TAGMSG #test")
        bob_msg = self.getMessage("bob")  # bob has echo-message
        alice_msg = self.getMessage("alice")
        # carol MUST NOT receive TAGMSG at all
        self.assertEqual(self.getMessages("carol"), [])
        # dave MUST NOT receive TAGMSG either, despite having server-time
        self.assertEqual(self.getMessages("dave"), [])
        for msg in [alice_msg, bob_msg]:
            self.assertMessageMatch(
                alice_msg,
                command="TAGMSG",
                params=["#test"],
                tags={
                    "+buzz": "fizz;buzz",
                    "+steel": "wootz",
                    "msgid": ANYSTR,
                    **ANYDICT,
                },
            )
            self.assertNotIn("cat", msg.tags)
        self.assertEqual(alice_msg.tags["msgid"], bob_msg.tags["msgid"])

    @pytest.mark.arbitrary_client_tags
    @cases.mark_capabilities("message-tags")
    @cases.mark_specifications("ircdocs")
    def testLengthLimits(self):
        self.connectClient(
            "alice",
            name="alice",
            capabilities=["message-tags", "echo-message"],
            skip_if_cap_nak=True,
        )
        self.joinChannel("alice", "#test")
        self.connectClient("bob", name="bob", capabilities=["message-tags"])
        self.joinChannel("bob", "#test")
        self.getMessages("alice")
        self.getMessages("bob")

        # this is right at the limit of 4094 bytes of server tag data,
        # 4096 bytes of client tag data (including the starting '@' and the final ' ')
        max_tagmsg = "@foo=bar;+baz=%s TAGMSG #test" % ("a" * 4081,)
        self.assertEqual(max_tagmsg.index("TAGMSG"), 4096)
        self.sendLine("alice", max_tagmsg)
        echo = self.getMessage("alice")
        relay = self.getMessage("bob")
        self.assertMessageMatch(
            echo,
            command="TAGMSG",
            params=["#test"],
            tags={"+baz": "a" * 4081, "msgid": StrRe(".+"), **ANYDICT},
        )
        self.assertMessageMatch(
            relay,
            command="TAGMSG",
            params=["#test"],
            tags={"+baz": "a" * 4081, "msgid": StrRe(".+"), **ANYDICT},
        )
        self.assertEqual(echo.tags["msgid"], relay.tags["msgid"])

        excess_tagmsg = "@foo=bar;+baz=%s TAGMSG #test" % ("a" * 4082,)
        self.assertEqual(excess_tagmsg.index("TAGMSG"), 4097)
        self.sendLine("alice", excess_tagmsg)
        reply = self.getMessage("alice")
        self.assertEqual(reply.command, ERR_INPUTTOOLONG)
        self.assertEqual(self.getMessages("bob"), [])

        max_privmsg = "@foo=bar;+baz=%s PRIVMSG #test %s" % ("a" * 4081, "b" * 496)
        # irctest adds the '\r\n' for us, this is right at the limit
        self.assertEqual(len(max_privmsg), 4096 + (512 - 2))
        self.sendLine("alice", max_privmsg)
        echo = self.getMessage("alice")
        # the server may still reject this message on the grounds that the final
        # parameter is too long to be relayed without truncation, once alice's
        # NUH is included. however, if the message was accepted, the tags MUST
        # be relayed intact, because they are unquestionably valid. See the
        # original context of ERR_INPUTTOOLONG:
        # https://defs.ircdocs.horse/defs/numerics.html#err-inputtoolong-417
        if echo.command != ERR_INPUTTOOLONG:
            relay = self.getMessage("bob")
            self.assertMessageMatch(
                echo,
                command="PRIVMSG",
                params=["#test", StrRe("b{400,496}")],
                tags={"+baz": "a" * 4081, "msgid": StrRe(".+"), **ANYDICT},
            )
            self.assertMessageMatch(
                relay,
                command="PRIVMSG",
                params=["#test", StrRe("b{400,496}")],
                tags={"+baz": "a" * 4081, "msgid": StrRe(".+"), **ANYDICT},
            )
            self.assertEqual(echo.tags["msgid"], relay.tags["msgid"])
            # message may have been truncated
            self.assertIn("b" * 400, echo.params[1])
            self.assertEqual(echo.params[1].rstrip("b"), "")
            self.assertIn("b" * 400, relay.params[1])
            self.assertEqual(relay.params[1].rstrip("b"), "")

        excess_privmsg = "@foo=bar;+baz=%s PRIVMSG #test %s" % ("a" * 4082, "b" * 495)
        # TAGMSG data is over the limit, but we're within the overall limit for a line
        self.assertEqual(excess_privmsg.index("PRIVMSG"), 4097)
        self.assertEqual(len(excess_privmsg), 4096 + (512 - 2))
        self.sendLine("alice", excess_privmsg)
        reply = self.getMessage("alice")
        self.assertEqual(reply.command, ERR_INPUTTOOLONG)
        self.assertEqual(self.getMessages("bob"), [])
