from irctest import cases, runner
from irctest.numerics import ERR_UNKNOWNCOMMAND, RPL_ENDOFLINKS, RPL_LINKS
from irctest.patma import ANYSTR, StrRe


class LinksTestCase(cases.BaseServerTestCase):
    def testLinksSingleServer(self):
        """
        Only testing the parameter-less case.

        https://datatracker.ietf.org/doc/html/rfc1459#section-4.3.3
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.4.5

        "
        364     RPL_LINKS
                        "<mask> <server> :<hopcount> <server info>"
        365     RPL_ENDOFLINKS
                        "<mask> :End of /LINKS list"

                - In replying to the LINKS message, a server must send
                  replies back using the RPL_LINKS numeric and mark the
                  end of the list using an RPL_ENDOFLINKS reply.
        "
        -- https://datatracker.ietf.org/doc/html/rfc1459#page-51
        -- https://datatracker.ietf.org/doc/html/rfc2812#page-48
        """
        self.connectClient("nick")
        self.sendLine(1, "LINKS")
        messages = self.getMessages(1)
        if messages[0].command == ERR_UNKNOWNCOMMAND:
            raise runner.NotImplementedByController("LINKS")
        self.assertMessageMatch(
            messages[0],
            command=RPL_LINKS,
            params=["nick", "My.Little.Server", "My.Little.Server", "0 test server"],
        )
        self.assertMessageMatch(
            messages[1],
            command=RPL_ENDOFLINKS,
            params=["nick", "*", ANYSTR],
        )


@cases.mark_services
class ServicesLinksTestCase(cases.BaseServerTestCase):
    # On every IRCd but Ergo, services are linked.
    # Ergo does not implement LINKS at all, so this test is skipped.
    def testLinksWithServices(self):
        """
        Only testing the parameter-less case.

        https://datatracker.ietf.org/doc/html/rfc1459#section-4.3.3
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.4.5

        "
        364     RPL_LINKS
                        "<mask> <server> :<hopcount> <server info>"
        365     RPL_ENDOFLINKS
                        "<mask> :End of /LINKS list"

                - In replying to the LINKS message, a server must send
                  replies back using the RPL_LINKS numeric and mark the
                  end of the list using an RPL_ENDOFLINKS reply.
        "
        -- https://datatracker.ietf.org/doc/html/rfc1459#page-51
        -- https://datatracker.ietf.org/doc/html/rfc2812#page-48
        """
        self.connectClient("nick")
        self.sendLine(1, "LINKS")
        messages = self.getMessages(1)

        if messages[0].command == ERR_UNKNOWNCOMMAND:
            raise runner.NotImplementedByController("LINKS")

        self.assertMessageMatch(
            messages.pop(-1),
            command=RPL_ENDOFLINKS,
            params=["nick", "*", ANYSTR],
        )

        messages.sort(key=lambda m: m.params[-1])

        self.assertMessageMatch(
            messages.pop(0),
            command=RPL_LINKS,
            params=["nick", "My.Little.Server", "My.Little.Server", "0 test server"],
        )
        self.assertMessageMatch(
            messages.pop(0),
            command=RPL_LINKS,
            params=["nick", "services.example.org", "My.Little.Server", StrRe("1 .+")],
        )

        self.assertEqual(messages, [])
