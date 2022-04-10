"""
The JOIN command  (`RFC 1459
<https://datatracker.ietf.org/doc/html/rfc1459#section-4.2.1>`__,
`RFC 2812 <https://datatracker.ietf.org/doc/html/rfc2812#section-3.2.1>`__,
`Modern <https://modern.ircdocs.horse/#join-message>`__)
"""

from irctest import cases
from irctest.irc_utils import ambiguities


class JoinTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812", strict=True)
    def testJoinAllMessages(self):
        """“If a JOIN is successful, the user receives a JOIN message as
        confirmation and is then sent the channel's topic (using RPL_TOPIC) and
        the list of users who are on the channel (using RPL_NAMREPLY), which
        MUST include the user joining.”
        -- <https://tools.ietf.org/html/rfc2812#section-3.2.1>

        “If a JOIN is successful, the user is then sent the channel's topic
        (using RPL_TOPIC) and the list of users who are on the channel (using
        RPL_NAMREPLY), which must include the user joining.”
        -- <https://tools.ietf.org/html/rfc1459#section-4.2.1>
        """
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        received_commands = {m.command for m in self.getMessages(1)}
        expected_commands = {"353", "366"}  # RPL_NAMREPLY  # RPL_ENDOFNAMES
        self.assertTrue(
            expected_commands.issubset(received_commands),
            "Server sent {} commands, but at least {} were expected.".format(
                received_commands, expected_commands
            ),
        )

    @cases.mark_specifications("RFC2812")
    def testJoinNamreply(self):
        """“353    RPL_NAMREPLY
            "( "=" / "*" / "@" ) <channel>
             :[ "@" / "+" ] <nick> *( " " [ "@" / "+" ] <nick> )”
        -- <https://tools.ietf.org/html/rfc2812#section-5.2>

        This test makes a user join and check what is sent to them.
        """
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")

        for m in self.getMessages(1):
            if m.command == "353":
                self.assertIn(
                    len(m.params),
                    (3, 4),
                    m,
                    fail_msg="RPL_NAM_REPLY with number of arguments "
                    "<3 or >4: {msg}",
                )
                params = ambiguities.normalize_namreply_params(m.params)
                self.assertIn(
                    params[1],
                    "=*@",
                    m,
                    fail_msg="Bad channel prefix: {item} not in {list}: {msg}",
                )
                self.assertEqual(
                    params[2],
                    "#chan",
                    m,
                    fail_msg="Bad channel name: {got} instead of " "{expects}: {msg}",
                )
                self.assertIn(
                    params[3],
                    {"foo", "@foo", "+foo"},
                    m,
                    fail_msg="Bad user list: should contain only user "
                    '"foo" with an optional "+" or "@" prefix, but got: '
                    "{msg}",
                )

    def testJoinTwice(self):
        self.connectClient("foo")
        self.sendLine(1, "JOIN #chan")
        m = self.getMessage(1)
        self.assertMessageMatch(m, command="JOIN", params=["#chan"])
        self.getMessages(1)
        self.sendLine(1, "JOIN #chan")
        # Note that there may be no message. Both RFCs require replies only
        # if the join is successful, or has an error among the given set.
        for m in self.getMessages(1):
            if m.command == "353":
                self.assertIn(
                    len(m.params),
                    (3, 4),
                    m,
                    fail_msg="RPL_NAM_REPLY with number of arguments "
                    "<3 or >4: {msg}",
                )
                params = ambiguities.normalize_namreply_params(m.params)
                self.assertIn(
                    params[1],
                    "=*@",
                    m,
                    fail_msg="Bad channel prefix: {item} not in {list}: {msg}",
                )
                self.assertEqual(
                    params[2],
                    "#chan",
                    m,
                    fail_msg="Bad channel name: {got} instead of " "{expects}: {msg}",
                )
                self.assertIn(
                    params[3],
                    {"foo", "@foo", "+foo"},
                    m,
                    fail_msg='Bad user list after user "foo" joined twice '
                    "the same channel: should contain only user "
                    '"foo" with an optional "+" or "@" prefix, but got: '
                    "{msg}",
                )
