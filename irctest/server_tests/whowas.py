from irctest import cases
from irctest.exceptions import ConnectionClosed
from irctest.numerics import (
    ERR_NONICKNAMEGIVEN,
    ERR_WASNOSUCHNICK,
    RPL_ENDOFWHOWAS,
    RPL_WHOISACTUALLY,
    RPL_WHOISSERVER,
    RPL_WHOWASUSER,
)
from irctest.patma import ANYSTR, StrRe


class WhowasTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasNumerics(self):
        """
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self.connectClient("nick1")

        self.connectClient("nick2")
        self.sendLine(2, "QUIT :bye")
        try:
            self.getMessages(2)
        except ConnectionClosed:
            pass

        self.sendLine(1, "WHOWAS nick2")

        messages = []
        for _ in range(10):
            messages.extend(self.getMessages(1))
            if RPL_ENDOFWHOWAS in (m.command for m in messages):
                break

        last_message = messages.pop()

        self.assertMessageMatch(
            last_message,
            command=RPL_ENDOFWHOWAS,
            params=["nick1", "nick2", ANYSTR],
            fail_msg=f"Last message was not RPL_ENDOFWHOWAS ({RPL_ENDOFWHOWAS})",
        )

        unexpected_messages = []

        # Straight from the RFCs
        for m in messages:
            if m.command == RPL_WHOWASUSER:
                host_re = "[0-9A-Za-z_:.-]+"
                self.assertMessageMatch(
                    m,
                    params=[
                        "nick1",
                        "nick2",
                        StrRe("~?username"),
                        StrRe(host_re),
                        "*",
                        "Realname",
                    ],
                )
            elif m.command == RPL_WHOISSERVER:
                self.assertMessageMatch(
                    m, params=["nick1", "nick2", "My.Little.Server", ANYSTR]
                )
            elif m.command == RPL_WHOISACTUALLY:
                # Technically not allowed by the RFCs, but Solanum uses it.
                # Not checking the syntax here; WhoisTestCase does it.
                pass
            else:
                unexpected_messages.append(m)

        self.assertEqual(
            unexpected_messages, [], fail_msg="Unexpected numeric messages: {got}"
        )

    def _testWhowasMultiple(self, second_result, whowas_command):
        """
        "The history is searched backward, returning the most recent entry first."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        # TODO: this test assumes the order is always: RPL_WHOWASUSER, then
        # optional RPL_WHOISACTUALLY, then RPL_WHOISSERVER; but the RFCs
        # don't specify the order.
        self.connectClient("nick1")

        self.connectClient("nick2", ident="ident2")
        self.sendLine(2, "QUIT :bye")
        try:
            self.getMessages(2)
        except ConnectionClosed:
            pass

        self.connectClient("nick2", ident="ident3")
        self.sendLine(3, "QUIT :bye")
        try:
            self.getMessages(3)
        except ConnectionClosed:
            pass

        self.sendLine(1, whowas_command)

        messages = self.getMessages(1)

        # nick2 with ident3
        self.assertMessageMatch(
            messages.pop(0),
            command=RPL_WHOWASUSER,
            params=[
                "nick1",
                "nick2",
                StrRe("~?ident3"),
                ANYSTR,
                "*",
                "Realname",
            ],
        )
        while messages[0].command in (RPL_WHOISACTUALLY, RPL_WHOISSERVER):
            # don't care
            messages.pop(0)

        if second_result:
            # nick2 with ident2
            self.assertMessageMatch(
                messages.pop(0),
                command=RPL_WHOWASUSER,
                params=[
                    "nick1",
                    "nick2",
                    StrRe("~?ident2"),
                    ANYSTR,
                    "*",
                    "Realname",
                ],
            )
            if messages[0].command == RPL_WHOISACTUALLY:
                # don't care
                messages.pop(0)
            while messages[0].command in (RPL_WHOISACTUALLY, RPL_WHOISSERVER):
                # don't care
                messages.pop(0)

        self.assertMessageMatch(
            messages.pop(0),
            command=RPL_ENDOFWHOWAS,
            params=["nick1", "nick2", ANYSTR],
            fail_msg=f"Last message was not RPL_ENDOFWHOWAS ({RPL_ENDOFWHOWAS})",
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasMultiple(self):
        """
        "The history is searched backward, returning the most recent entry first."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self._testWhowasMultiple(second_result=True, whowas_command="WHOWAS nick2")

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasCount1(self):
        """
        "If there are multiple entries, up to <count> replies will be returned"
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self._testWhowasMultiple(second_result=False, whowas_command="WHOWAS nick2 1")

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasCount2(self):
        """
        "If there are multiple entries, up to <count> replies will be returned"
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self._testWhowasMultiple(second_result=True, whowas_command="WHOWAS nick2 2")

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasCountNegative(self):
        """
        "If a non-positive number is passed as being <count>, then a full search
        is done."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self._testWhowasMultiple(second_result=True, whowas_command="WHOWAS nick2 -1")

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasCountZero(self):
        """
        "If a non-positive number is passed as being <count>, then a full search
        is done."
        -- https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self._testWhowasMultiple(second_result=True, whowas_command="WHOWAS nick2 0")

    @cases.mark_specifications("RFC2812", deprecated=True)
    def testWhowasWildcard(self):
        """
        "Wildcards are allowed in the <target> parameter."
        -- https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3
        """
        self._testWhowasMultiple(second_result=True, whowas_command="WHOWAS *ck2")

    @cases.mark_specifications("RFC1459", "RFC2812", deprecated=True)
    def testWhowasNoParam(self):
        """
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3

        and:

        "At the end of all reply batches, there must be RPL_ENDOFWHOWAS
        (even if there was only one reply and it was an error)."
        -- https://datatracker.ietf.org/doc/html/rfc1459#page-50
        -- https://datatracker.ietf.org/doc/html/rfc2812#page-45
        """
        # But no one seems to follow this. Most implementations use ERR_NEEDMOREPARAMS
        # instead of ERR_NONICKNAMEGIVEN; and I couldn't find any that returns
        # RPL_ENDOFWHOWAS either way.
        self.connectClient("nick1")

        self.sendLine(1, "WHOWAS")

        self.assertMessageMatch(
            self.getMessage(1),
            command=ERR_NONICKNAMEGIVEN,
            params=["nick1", ANYSTR],
        )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFWHOWAS,
            params=["nick1", "nick2", ANYSTR],
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testWhowasNoSuchNick(self):
        """
        https://datatracker.ietf.org/doc/html/rfc1459#section-4.5.3
        https://datatracker.ietf.org/doc/html/rfc2812#section-3.6.3

        and:

        "At the end of all reply batches, there must be RPL_ENDOFWHOWAS
        (even if there was only one reply and it was an error)."
        -- https://datatracker.ietf.org/doc/html/rfc1459#page-50
        -- https://datatracker.ietf.org/doc/html/rfc2812#page-45
        """
        self.connectClient("nick1")

        self.sendLine(1, "WHOWAS nick2")

        self.assertMessageMatch(
            self.getMessage(1),
            command=ERR_WASNOSUCHNICK,
            params=["nick1", "nick2", ANYSTR],
        )

        self.assertMessageMatch(
            self.getMessage(1),
            command=RPL_ENDOFWHOWAS,
            params=["nick1", "nick2", ANYSTR],
        )
