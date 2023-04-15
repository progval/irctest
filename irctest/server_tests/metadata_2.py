"""
`IRCv3 Metadata 2 <https://github.com/ircv3/ircv3-specifications/pull/501>`_
(not to be confused with the `deprecated IRCv3 Metadata
<https://ircv3.net/specs/core/metadata-3.2>`_)
"""

from irctest import cases
from irctest.patma import ANYDICT, ANYSTR, StrRe


class MetadataTestCase(cases.BaseServerTestCase):
    valid_metadata_keys = {"valid_key1", "valid_key2"}
    invalid_metadata_keys = {"invalid_key1", "invalid_key2"}

    def getBatchMessages(self, client):
        messages = self.getMessages(1)

        first_msg = messages.pop(0)
        last_msg = messages.pop(-1)
        self.assertMessageMatch(
            first_msg, command="BATCH", params=[StrRe(r"\+.*"), "metadata"]
        )
        batch_id = first_msg.params[0][1:]
        self.assertMessageMatch(last_msg, command="BATCH", params=["-" + batch_id])

        return (batch_id, messages)

    @cases.mark_specifications("IRCv3")
    def testGetOneUnsetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.sendLine(1, "METADATA * GET valid_key1")

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
        self.sendLine(1, "METADATA * GET valid_key1 valid_key2")
        (batch_id, messages) = self.getBatchMessages(1)
        self.assertEqual(len(messages), 2, fail_msg="Expected two ERR_NOMATCHINGKEY")
        self.assertMessageMatch(
            messages[0],
            command="766",  # RPL_NOMATCHINGKEY
            fail_msg="Did not reply with 766 (RPL_NOMATCHINGKEY) to a "
            "request to two unset valid METADATA key: {msg}",
        )
        self.assertMessageMatch(
            messages[0],
            params=["foo", "foo", "valid_key1", ANYSTR],
            fail_msg="Response to “METADATA * GET valid_key1 valid_key2” "
            "did not respond to valid_key1 first: {msg}",
        )
        self.assertMessageMatch(
            messages[1],
            command="766",  # ERR_NOMATCHINGKEY
            fail_msg="Did not reply with two 766 (ERR_NOMATCHINGKEY) to a "
            "request to two unset valid METADATA key: {msg}",
        )
        self.assertMessageMatch(
            messages[1],
            params=["foo", "foo", "valid_key2", ANYSTR],
            fail_msg="Response to “METADATA * GET valid_key1 valid_key2” "
            "did not respond to valid_key2 as second response: {msg}",
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

    def assertSetValue(self, target, key, value):
        self.sendLine(1, "METADATA {} SET {} :{}".format(target, key, value))

        if target == "*":
            target = StrRe(r"(\*|foo)")

        self.assertMessageMatch(
            self.getMessage(1),
            command="761",  # RPL_KEYVALUE
            params=["foo", target, key, ANYSTR, value],
        )

    def assertGetValue(self, target, key, value):
        self.sendLine(1, "METADATA {} GET {}".format(target, key))

        if target == "*":
            target = StrRe(r"(\*|foo)")

        (batch_id, messages) = self.getBatchMessages(1)
        self.assertEqual(len(messages), 1, fail_msg="Expected one RPL_KEYVALUE")
        self.assertMessageMatch(
            messages[0],
            command="761",  # RPL_KEYVALUE
            params=["foo", target, key, ANYSTR, value],
        )

    def assertSetGetValue(self, target, key, value):
        self.assertSetValue(target, key, value)
        self.assertGetValue(target, key, value)

    @cases.mark_specifications("IRCv3")
    def testSetGetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        self.assertSetGetValue("*", "valid_key1", "myvalue")

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
            "*",
            "valid_key1",
            "->{}<-".format(heart),
        )

    def _testSetInvalidValue(self, value):
        self.connectClient(
            "foo", capabilities=["draft/metadata-2", "batch"], skip_if_cap_nak=True
        )
        # Sending directly because it is not valid UTF-8 so Python would
        # not like it
        self.clients[1].conn.sendall(
            b"METADATA * SET valid_key1 " b":invalid UTF-8 ->\xc3<-\r\n"
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
        self.clients[1].conn.sendall(b"METADATA * SET valid_key1 :" + value + b"\r\n")
        self.assertMessageMatch(
            self.getMessage(1),
            command="FAIL",
            params=["METADATA", "INVALID_VALUE", ANYSTR],
        )
        messages = self.getMessages(1)
        self.assertNotIn(
            "761",  # RPL_KEYVALUE
            {m.command for m in messages},
            fail_msg="Setting METADATA key to a value containing invalid "
            "UTF-8 was answered with 761 (RPL_KEYVALUE)",
        )
        self.assertEqual(
            messages,
            [],
            fail_msg="Unexpected response to METADATA SET with invalid value: {got}",
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
