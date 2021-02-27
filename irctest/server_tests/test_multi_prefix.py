"""
Tests multi-prefix.
<http://ircv3.net/specs/extensions/multi-prefix-3.1.html>
"""

from irctest import cases


class MultiPrefixTestCase(cases.BaseServerTestCase):
    @cases.mark_capabilities("multi-prefix")
    def testMultiPrefix(self):
        """“When requested, the multi-prefix client capability will cause the
        IRC server to send all possible prefixes which apply to a user in NAMES
        and WHO output.

        These prefixes MUST be in order of ‘rank’, from highest to lowest.
        """
        self.connectClient("foo", capabilities=["multi-prefix"])
        self.joinChannel(1, "#chan")
        self.sendLine(1, "MODE #chan +v foo")
        self.getMessages(1)

        # TODO(dan): Make sure +v is voice

        self.sendLine(1, "NAMES #chan")
        reply = self.getMessage(1)
        self.assertMessageEqual(
            reply,
            command="353",
            fail_msg="Expected NAMES response (353) with @+foo, got: {msg}",
        )
        self.assertMessageEqual(
            reply,
            command="353",
            params=["foo", reply.params[1], "#chan", "@+foo"],
            fail_msg="Expected NAMES response (353) with @+foo, got: {msg}",
        )
        self.getMessages(1)

        self.sendLine(1, "WHO #chan")
        msg = self.getMessage(1)
        self.assertEqual(
            msg.command, "352", msg, fail_msg="Expected WHO response (352), got: {msg}"
        )
        self.assertGreaterEqual(
            len(msg.params),
            8,
            "Expected WHO response (352) with 8 params, got: {msg}".format(msg=msg),
        )
        self.assertTrue(
            "@+" in msg.params[6],
            'Expected WHO response (352) with "@+" in param 7, got: {msg}'.format(
                msg=msg
            ),
        )
