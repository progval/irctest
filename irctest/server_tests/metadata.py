"""
`Deprecated IRCv3 Metadata <https://ircv3.net/specs/core/metadata-3.2>`_
"""

from irctest import cases


class MetadataDeprecatedTestCase(cases.BaseServerTestCase):
    valid_metadata_keys = {"display-name", "avatar"}
    invalid_metadata_keys = {"indisplay-name", "inavatar"}

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testInIsupport(self):
        """“If METADATA is supported, it MUST be specified in RPL_ISUPPORT
        using the METADATA key.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html>
        """
        self.addClient()
        self.sendLine(1, "CAP LS 302")
        self.getCapLs(1)
        self.sendLine(1, "USER foo foo foo :foo")
        self.sendLine(1, "NICK foo")
        self.sendLine(1, "CAP END")
        self.skipToWelcome(1)
        m = self.getMessage(1)
        while m.command != "005":  # RPL_ISUPPORT
            m = self.getMessage(1)
        self.assertIn(
            "METADATA",
            {x.split("=")[0] for x in m.params[1:-1]},
            fail_msg="{item} missing from RPL_ISUPPORT",
        )
        self.getMessages(1)

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testGetOneUnsetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>"""
        self.connectClient("foo")
        self.sendLine(1, "METADATA * GET display-name")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="766",  # ERR_NOMATCHINGKEY
            fail_msg="Did not reply with 766 (ERR_NOMATCHINGKEY) to a "
            "request to an unset valid METADATA key.",
        )

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testGetTwoUnsetValid(self):
        """“Multiple keys may be given. The response will be either RPL_KEYVALUE,
        ERR_KEYINVALID or ERR_NOMATCHINGKEY for every key in order.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>
        """
        self.connectClient("foo")
        self.sendLine(1, "METADATA * GET display-name avatar")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="766",  # ERR_NOMATCHINGKEY
            fail_msg="Did not reply with 766 (ERR_NOMATCHINGKEY) to a "
            "request to two unset valid METADATA key: {msg}",
        )
        self.assertEqual(
            m.params[1],
            "display-name",
            m,
            fail_msg="Response to “METADATA * GET display-name avatar” "
            "did not respond to display-name first: {msg}",
        )
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="766",  # ERR_NOMATCHINGKEY
            fail_msg="Did not reply with two 766 (ERR_NOMATCHINGKEY) to a "
            "request to two unset valid METADATA key: {msg}",
        )
        self.assertEqual(
            m.params[1],
            "avatar",
            m,
            fail_msg="Response to “METADATA * GET display-name avatar” "
            "did not respond to avatar as second response: {msg}",
        )

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testListNoSet(self):
        """“This subcommand MUST list all currently-set metadata keys along
        with their values. The response will be zero or more RPL_KEYVALUE
        events, following by RPL_METADATAEND event.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-list>
        """
        self.connectClient("foo")
        self.sendLine(1, "METADATA * LIST")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="762",  # RPL_METADATAEND
            fail_msg="Response to “METADATA * LIST” was not "
            "762 (RPL_METADATAEND) but: {msg}",
        )

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testListInvalidTarget(self):
        """“In case of invalid target RPL_METADATAEND MUST NOT be sent.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-list>
        """
        self.connectClient("foo")
        self.sendLine(1, "METADATA foobar LIST")
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="765",  # ERR_TARGETINVALID
            fail_msg="Response to “METADATA <invalid target> LIST” was "
            "not 765 (ERR_TARGETINVALID) but: {msg}",
        )
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn(
            "762",
            commands,
            fail_msg="Sent “METADATA <invalid target> LIST”, got 765 "
            "(ERR_TARGETINVALID), and then 762 (RPL_METADATAEND)",
        )

    def assertSetValue(self, target, key, value, displayable_value=None):
        if displayable_value is None:
            displayable_value = value
        self.sendLine(1, "METADATA {} SET {} :{}".format(target, key, value))
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="761",  # RPL_KEYVALUE
            fail_msg="Did not reply with 761 (RPL_KEYVALUE) to a valid "
            "“METADATA * SET {} :{}”: {msg}",
            extra_format=(key, displayable_value),
        )
        self.assertEqual(
            m.params[1],
            "display-name",
            m,
            fail_msg="Second param of 761 after setting “{expects}” to "
            "“{}” is not “{expects}”: {msg}.",
            extra_format=(displayable_value,),
        )
        self.assertEqual(
            m.params[3],
            value,
            m,
            fail_msg="Fourth param of 761 after setting “{0}” to "
            "“{1}” is not “{1}”: {msg}.",
            extra_format=(key, displayable_value),
        )
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="762",  # RPL_METADATAEND
            fail_msg="Did not send RPL_METADATAEND after setting "
            "a valid METADATA key.",
        )

    def assertGetValue(self, target, key, value, displayable_value=None):
        self.sendLine(1, "METADATA * GET {}".format(key))
        m = self.getMessage(1)
        self.assertMessageMatch(
            m,
            command="761",  # RPL_KEYVALUE
            fail_msg="Did not reply with 761 (RPL_KEYVALUE) to a valid "
            "“METADATA * GET” when the key is set is set: {msg}",
        )
        self.assertEqual(
            m.params[1],
            key,
            m,
            fail_msg="Second param of 761 after getting “{expects}” "
            "(which is set) is not “{expects}”: {msg}.",
        )
        self.assertEqual(
            m.params[3],
            value,
            m,
            fail_msg="Fourth param of 761 after getting “{0}” "
            "(which is set to “{1}”) is not ”{1}”: {msg}.",
            extra_format=(key, displayable_value),
        )

    def assertSetGetValue(self, target, key, value, displayable_value=None):
        self.assertSetValue(target, key, value, displayable_value)
        self.assertGetValue(target, key, value, displayable_value)

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testSetGetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>"""
        self.connectClient("foo")
        self.assertSetGetValue("*", "display-name", "myvalue")

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testSetGetZeroCharInValue(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        self.connectClient("foo")
        self.assertSetGetValue("*", "display-name", "zero->\0<-zero", "zero->\\0<-zero")

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testSetGetHeartInValue(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        heart = b"\xf0\x9f\x92\x9c".decode()
        self.connectClient("foo")
        self.assertSetGetValue(
            "*",
            "display-name",
            "->{}<-".format(heart),
            "zero->{}<-zero".format(heart.encode()),
        )

    @cases.mark_specifications("IRCv3", deprecated=True)
    def testSetInvalidUtf8(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        self.connectClient("foo")
        # Sending directly because it is not valid UTF-8 so Python would
        # not like it
        self.clients[1].conn.sendall(
            b"METADATA * SET display-name " b":invalid UTF-8 ->\xc3<-\r\n"
        )
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn(
            "761",
            commands,  # RPL_KEYVALUE
            fail_msg="Setting METADATA key to a value containing invalid "
            "UTF-8 was answered with 761 (RPL_KEYVALUE)",
        )
        self.clients[1].conn.sendall(
            b"METADATA * SET display-name " b":invalid UTF-8: \xc3\r\n"
        )
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn(
            "761",
            commands,  # RPL_KEYVALUE
            fail_msg="Setting METADATA key to a value containing invalid "
            "UTF-8 was answered with 761 (RPL_KEYVALUE)",
        )
