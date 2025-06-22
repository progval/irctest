"""
`IRCv3 Metadata 2 <https://github.com/ircv3/ircv3-specifications/pull/501>`_
(not to be confused with the `deprecated IRCv3 Metadata
<https://ircv3.net/specs/core/metadata-3.2>`_)
"""

import itertools

import pytest

from irctest import cases, runner
from irctest.numerics import RPL_METADATASUBOK
from irctest.patma import ANYDICT, ANYLIST, ANYOPTSTR, ANYSTR, Either, StrRe

CLIENT_NICKS = {
    1: "foo",
    2: "bar",
}


class MetadataTestCase(cases.BaseServerTestCase):
    def getBatchMessages(self, client):
        messages = self.getMessages(client)

        first_msg = messages.pop(0)
        last_msg = messages.pop(-1)
        # TODO: s/ANYOPTSTR/ANYSTR/, as per spec update to require a batch parameter
        # indicating the target
        self.assertMessageMatch(
            first_msg, command="BATCH", params=[StrRe(r"\+.*"), "metadata", ANYOPTSTR]
        )
        batch_id = first_msg.params[0][1:]
        self.assertMessageMatch(last_msg, command="BATCH", params=["-" + batch_id])

        return (batch_id, messages)

    def sub(self, client, keys):
        self.sendLine(2, "METADATA * SUB " + " ".join(keys))
        acknowledged_subs = []
        for m in self.getMessages(2):
            self.assertMessageMatch(
                m,
                command="770",  # RPL_METADATASUBOK
                params=["bar", *ANYLIST],
            )
            acknowledged_subs.extend(m.params[1:])
        self.assertEqual(
            sorted(acknowledged_subs),
            sorted(keys),
            fail_msg="Expected RPL_METADATASUBOK to ack {expects}, got {got}",
        )

    @cases.mark_specifications("IRCv3")
    def testGetOneUnsetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.sendLine(1, "METADATA * GET display-name")

        (batch_id, messages) = self.getBatchMessages(1)
        self.assertEqual(len(messages), 1, fail_msg="Expected one ERR_NOMATCHINGKEY")
        self.assertMessageMatch(
            messages[0],
            tags={"batch": batch_id, **ANYDICT},
            command="766",  # ERR_NOMATCHINGKEY
            fail_msg="Did not reply with 766 (ERR_NOMATCHINGKEY) to a "
            "request to an unset valid METADATA key: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    def testGetTwoUnsetValid(self):
        """“Multiple keys may be given. The response will be either RPL_KEYVALUE,
        ERR_KEYINVALID or ERR_NOMATCHINGKEY for every key in order.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>
        """
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.sendLine(1, "METADATA * GET display-name avatar")
        (batch_id, messages) = self.getBatchMessages(1)
        self.assertEqual(len(messages), 2, fail_msg="Expected two ERR_NOMATCHINGKEY")
        self.assertMessageMatch(
            messages[0],
            command="766",  # RPL_KEYNOTSET
            fail_msg="Did not reply with 766 (RPL_KEYNOTSET) to a "
            "request to two unset valid METADATA key: {msg}",
        )
        self.assertMessageMatch(
            messages[0],
            params=["foo", "foo", "display-name", ANYSTR],
            fail_msg="Response to “METADATA * GET display-name avatar” "
            "did not respond to display-name first: {msg}",
        )
        self.assertMessageMatch(
            messages[1],
            command="766",  # RPL_KEYNOTSET
            fail_msg="Did not reply with two 766 (RPL_KEYNOTSET) to a "
            "request to two unset valid METADATA key: {msg}",
        )
        self.assertMessageMatch(
            messages[1],
            params=["foo", "foo", "avatar", ANYSTR],
            fail_msg="Response to “METADATA * GET display-name avatar” "
            "did not respond to avatar as second response: {msg}",
        )

    @cases.mark_specifications("IRCv3")
    def testListNoSet(self):
        """“This subcommand MUST list all currently-set metadata keys along
        with their values. The response will be zero or more RPL_KEYVALUE
        events, following by RPL_METADATAEND event.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-list>
        """
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.sendLine(1, "METADATA * LIST")
        (batch_id, messages) = self.getBatchMessages(1)
        self.assertEqual(len(messages), 0, fail_msg="Expected empty batch")

    @cases.mark_specifications("IRCv3")
    def testListInvalidTarget(self):
        """“In case of invalid target RPL_METADATAEND MUST NOT be sent.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-list>
        """
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.sendLine(1, "METADATA foobar LIST")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="FAIL",
            params=["METADATA", "INVALID_TARGET", "foobar", ANYSTR],
            fail_msg="Response to “METADATA <invalid target> LIST” was "
            "not 765 (ERR_TARGETINVALID) but: {msg}",
        )
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn(
            "762",
            commands,
            fail_msg="Sent “METADATA <invalid target> LIST”, got FAIL INVALID_TARGET, "
            "and then 762 (RPL_METADATAEND)",
        )

    def assertSetValue(self, client, target, key, value, before_connect=False):
        self.sendLine(client, "METADATA {} SET {} :{}".format(target, key, value))

        if target == "*":
            target = Either("*", CLIENT_NICKS[client])

        nick = CLIENT_NICKS[client]
        if before_connect:
            nick = Either("*", nick)

        self.assertMessageMatch(
            self.getMessage(client),
            command="761",  # RPL_KEYVALUE
            params=[nick, target, key, ANYSTR, value],
        )

    def assertUnsetValue(self, client, target, key):
        self.sendLine(client, "METADATA {} SET {}".format(target, key))

        if target == "*":
            target = Either("*", CLIENT_NICKS[client])

        self.assertMessageMatch(
            self.getMessage(client),
            command="766",  # RPL_KEYNOTSET
            params=[CLIENT_NICKS[client], target, key, ANYSTR],
        )

    def assertGetValue(self, client, target, key, value, before_connect=False):
        self.sendLine(client, "METADATA {} GET {}".format(target, key))

        if target == "*":
            target = Either("*", CLIENT_NICKS[client])

        nick = CLIENT_NICKS[client]
        if before_connect:
            nick = Either("*", nick)

        (batch_id, messages) = self.getBatchMessages(client)
        self.assertEqual(len(messages), 1, fail_msg="Expected one RPL_KEYVALUE")
        self.assertMessageMatch(
            messages[0],
            command="761",  # RPL_KEYVALUE
            params=[nick, target, key, ANYSTR, value],
        )

    def assertValueNotSet(self, client, target, key):
        self.sendLine(client, "METADATA {} GET {}".format(target, key))

        if target == "*":
            target = Either("*", CLIENT_NICKS[client])

        (batch_id, messages) = self.getBatchMessages(client)
        self.assertEqual(len(messages), 1, fail_msg="Expected one RPL_KEYVALUE")
        self.assertMessageMatch(
            messages[0],
            command="766",  # RPL_KEYNOTSET
            params=[CLIENT_NICKS[client], target, key, ANYSTR],
        )

    def assertSetGetValue(self, client, target, key, value):
        self.assertSetValue(client, target, key, value)
        self.assertGetValue(client, target, key, value)

    def assertUnsetGetValue(self, client, target, key):
        self.assertUnsetValue(client, target, key)
        self.assertValueNotSet(client, target, key)

    @pytest.mark.parametrize(
        "set_target,get_target", itertools.product(["*", "foo"], ["*", "foo"])
    )
    @cases.mark_specifications("IRCv3")
    def testSetGetUser(self, set_target, get_target):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.assertSetGetValue(1, set_target, "display-name", "Foo The First")

    @cases.mark_specifications("IRCv3")
    def testSetGetUserAgain(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.assertSetGetValue(1, "*", "display-name", "Foo The First")
        self.assertSetGetValue(1, "*", "display-name", "Foo The Second")

    @cases.mark_specifications("IRCv3")
    def testSetUnsetUser(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.assertSetGetValue(1, "*", "display-name", "Foo The First")
        self.assertUnsetGetValue(1, "*", "display-name")

    @cases.mark_specifications("IRCv3")
    def testGetOtherUser(self):
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        # As of 2023-04-15, the Unreal module requires users to share a channel for
        # metadata to be visible to each other
        self.sendLine(1, "JOIN #chan")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(1)

        self.assertSetValue(1, "*", "display-name", "Foo The First")
        self.assertEqual(
            self.getMessages(2),
            [],
            fail_msg="Unexpected messages after other user used METADATA SET: {got}",
        )
        self.assertGetValue(2, "foo", "display-name", "Foo The First")

    @cases.mark_specifications("IRCv3")
    def testSetOtherUser(self):
        """Not required by the spec, but it makes little sense to allow anyone to
        write a channel's metadata"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        # As of 2023-04-15, the Unreal module requires users to share a channel for
        # metadata to be visible to each other.
        self.sendLine(1, "JOIN #chan")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(1)

        self.sendLine(1, "METADATA bar SET display-name :Totally Not Foo")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["METADATA", "KEY_NO_PERMISSION", "bar", "display-name", ANYSTR],
        )

        self.assertEqual(
            self.getMessages(2),
            [],
            fail_msg="Unexpected messages after other user used METADATA SET: {got}",
        )

    @cases.mark_specifications("IRCv3")
    def testSubUser(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.sub(2, ["avatar", "display-name"])

        self.sendLine(1, "JOIN #chan")
        self.sendLine(2, "JOIN #chan")
        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(1)

        self.assertSetGetValue(1, "*", "display-name", "Foo The First")
        self.assertMessageMatch(
            self.getMessage(2),
            command="METADATA",
            params=["foo", "display-name", ANYSTR, "Foo The First"],
        )

        self.assertSetGetValue(1, "*", "display-name", "Foo The Second")
        self.assertMessageMatch(
            self.getMessage(2),
            command="METADATA",
            params=["foo", "display-name", ANYSTR, "Foo The Second"],
        )

        self.assertUnsetGetValue(1, "*", "display-name")
        self.assertMessageMatch(
            self.getMessage(2),
            command="METADATA",
            params=["foo", "display-name", ANYSTR],
        )

    @cases.mark_specifications("IRCv3")
    def testSubUserSetBeforeJoin(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.sub(2, ["display-name", "avatar"])

        self.assertSetGetValue(1, "*", "display-name", "Foo The First")
        self.assertEqual(
            self.getMessages(2),
            [],
            fail_msg="'bar' got message when 'foo' set its display-name even though "
            "they don't share a channel",
        )

        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)
        self.sendLine(2, "JOIN #chan")

        messages = self.getMessages(2)
        metadata_messages = [m for m in messages if m.command == "METADATA"]

        self.assertEqual(
            len(metadata_messages),
            1,
            fail_msg="Expected exactly one METADATA message when joining a channel, "
            "got: {got}",
        )

        self.assertMessageMatch(
            metadata_messages[0],
            command="METADATA",
            params=["foo", "display-name", ANYSTR, "Foo The First"],
        )

    @cases.mark_specifications("IRCv3")
    def testSetGetChannel(self):
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.joinChannel(1, "#chan")
        self.joinChannel(2, "#chan")
        self.getMessages(1)

        self.assertSetGetValue(1, "#chan", "display-name", "Hash Channel")
        self.assertEqual(
            self.getMessages(2),
            [],
            fail_msg="Unexpected messages after other user used METADATA SET: {got}",
        )
        self.assertGetValue(2, "#chan", "display-name", "Hash Channel")

    @cases.mark_specifications("IRCv3")
    def testSetUnsetChannel(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.joinChannel(1, "#chan")
        self.joinChannel(2, "#chan")
        self.getMessages(1)

        self.assertSetGetValue(1, "#chan", "display-name", "Hash Channel")
        self.assertUnsetGetValue(1, "#chan", "display-name")
        self.assertEqual(
            self.getMessages(2),
            [],
            fail_msg="Unexpected messages after other user used METADATA SET: {got}",
        )
        self.assertValueNotSet(2, "#chan", "display-name")

    @cases.mark_specifications("IRCv3")
    def testSetGetChannelNotOp(self):
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.joinChannel(1, "#chan")
        self.joinChannel(2, "#chan")
        self.getMessages(1)

        self.sendLine(2, "METADATA #chan SET display-name :Sharp Channel")
        self.assertMessageMatch(
            self.getMessage(2),
            command="FAIL",
            params=["METADATA", "KEY_NO_PERMISSION", "#chan", "display-name", ANYSTR],
        )

        self.assertEqual(
            self.getMessages(1),
            [],
            fail_msg="Unexpected messages after other user used METADATA SET: {got}",
        )

    @cases.mark_specifications("IRCv3")
    def testSubChannel(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.sub(2, ["avatar", "display-name"])

        self.joinChannel(1, "#chan")
        self.joinChannel(2, "#chan")
        self.getMessages(1)

        self.assertSetGetValue(1, "#chan", "display-name", "Hash Channel")
        self.assertMessageMatch(
            self.getMessage(2),
            command="METADATA",
            params=["#chan", "display-name", ANYSTR, "Hash Channel"],
        )

        self.assertSetGetValue(1, "#chan", "display-name", "Harsh Channel")
        self.assertMessageMatch(
            self.getMessage(2),
            command="METADATA",
            params=["#chan", "display-name", ANYSTR, "Harsh Channel"],
        )

    @cases.mark_specifications("IRCv3")
    def testSubChannelSetBeforeJoin(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )

        self.sub(2, ["display-name", "avatar"])

        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)

        self.assertSetGetValue(1, "#chan", "display-name", "Hash Channel")
        self.assertEqual(
            self.getMessages(2),
            [],
            fail_msg="'bar' got message when 'foo' set #chan's display-name even "
            "though they are not in it",
        )

        self.sendLine(2, "JOIN #chan")

        messages = self.getMessages(2)
        metadata_messages = [m for m in messages if m.command == "METADATA"]

        self.assertEqual(
            len(metadata_messages),
            1,
            fail_msg="Expected exactly one METADATA message when joining a channel, "
            "got: {got}",
        )

        self.assertMessageMatch(
            metadata_messages[0],
            command="METADATA",
            params=["#chan", "display-name", ANYSTR, "Hash Channel"],
        )

    @cases.mark_specifications("IRCv3")
    def testSetGetValidBeforeConnect(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.addClient(1)

        self.sendLine(1, "CAP LS 302")
        caps = self.getCapLs(1)
        if "before-connect" not in (caps.get("draft/metadata-2") or "").split(","):
            raise runner.OptionalExtensionNotSupported(
                "draft/metadata-2=before-connect"
            )

        self.requestCapabilities(1, ["draft/metadata-2", "batch"], skip_if_cap_nak=True)

        self.assertSetValue(
            1, "*", "display-name", "Foo The First", before_connect=True
        )

        self.sendLine(1, "NICK foo")
        self.sendLine(1, "USER foo 0 * :foo")
        self.sendLine(1, "CAP END")
        burst = self.getMessages(1)

        burst_batch = []
        batch_id = ""
        for msg in burst:
            if (
                batch_id == ""
                and msg.command == "BATCH"
                and len(msg.params) >= 3
                and msg.params[1] == "metadata"
            ):
                batch_id = msg.params[0][1:]
            elif batch_id != "":
                if msg.command == "BATCH" and msg.params[0] == "-" + batch_id:
                    batch_id = ""
                else:
                    burst_batch.append(msg)
        self.assertGreater(
            len(burst_batch), 0, "Must receive METADATA lines for pre-set metadata"
        )
        self.assertTrue(
            any(
                self.messageEqual(
                    msg,
                    command="METADATA",
                    params=["foo", "display-name", ANYSTR, "Foo The First"],
                )
                for msg in burst_batch
            )
        )

        self.assertGetValue(1, "*", "display-name", "Foo The First")

    @cases.mark_specifications("IRCv3")
    def testSetGetHeartInValue(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        heart = b"\xf0\x9f\x92\x9c".decode()
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.assertSetGetValue(
            1,
            "*",
            "display-name",
            "->{}<-".format(heart),
        )

    def _testSetInvalidValue(self, value):
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.connectClient(
            "bar", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.joinChannel(1, "#chan")
        self.joinChannel(2, "#chan")
        self.getMessages(1)
        self.sendLine(2, "METADATA * SUB display-name")
        sub_replies = self.getMessages(2)
        self.assertEqual(
            len(sub_replies), 1, "Successful sub should get exactly 1 reply"
        )
        self.assertMessageMatch(
            sub_replies[0],
            command=RPL_METADATASUBOK,
            params=["bar", "display-name"],
        )

        # Sending directly because it is not valid UTF-8 so Python would
        # not like it
        self.clients[1].conn.sendall(
            b"METADATA * SET display-name :invalid UTF-8 ->\xc3<-\r\n"
        )
        try:
            commands = {m.command for m in self.getMessages(1)}
        except UnicodeDecodeError:
            assert False, "Server sent invalid UTF-8"
        self.assertNotIn(
            "761",
            commands,  # RPL_KEYVALUE
            fail_msg="Setting METADATA key to a value containing invalid "
            "UTF-8 was answered with 761 (RPL_KEYVALUE)",
        )
        self.clients[1].conn.sendall(b"METADATA * SET display-name :" + value + b"\r\n")
        messages = self.getMessages(1)
        # must get a FAIL and not a successful 761 RPL_KEYVALUE response
        self.assertEqual(
            len(messages),
            1,
            "Invalid METADATA value should produce exactly one FAIL message",
        )
        failMessage = messages[0]
        self.assertMessageMatch(
            failMessage,
            command="FAIL",
            params=["METADATA", ANYSTR, ANYSTR],
        )
        # VALUE_INVALID as per the metadata spec, INVALID_UTF8 as per the UTF8ONLY spec
        self.assertIn(failMessage.params[1], ("VALUE_INVALID", "INVALID_UTF8"))
        # friends should not receive anything
        self.assertEqual(
            self.getMessages(2), [], "Unsuccessful metadata update must not be relayed"
        )

    @cases.mark_specifications("IRCv3")
    def testSetInvalidUtf8(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        self._testSetInvalidValue(b"invalid UTF-8: \xc3")

    @cases.mark_specifications("IRCv3")
    def testSetTooManyChars(self):
        """Assumes all servers reject values over 480 bytes. This isn't required by the
        spec, but makes them risk overflowing when printing the value, so they probably
        won't allow that.
        """
        self._testSetInvalidValue(b"abcd" * 120)

    @cases.mark_specifications("IRCv3")
    def testSetTooManyBytes(self):
        """Assumes all servers reject values over 480 bytes. This isn't required by the
        spec, but makes them risk overflowing when printing the value, so they probably
        won't allow that.
        """
        heart = b"\xf0\x9f\x92\x9c"
        self._testSetInvalidValue(heart * 120)
