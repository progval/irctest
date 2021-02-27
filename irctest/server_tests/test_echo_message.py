"""
<http://ircv3.net/specs/extensions/echo-message-3.2.html>
"""

from irctest import cases
from irctest.basecontrollers import NotImplementedByController
from irctest.irc_utils.junkdrawer import random_name


class DMEchoMessageTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Oragono")
    def testDirectMessageEcho(self):
        bar = random_name("bar")
        self.connectClient(
            bar,
            name=bar,
            capabilities=[
                "batch",
                "labeled-response",
                "echo-message",
                "message-tags",
                "server-time",
            ],
        )
        self.getMessages(bar)

        qux = random_name("qux")
        self.connectClient(
            qux,
            name=qux,
            capabilities=[
                "batch",
                "labeled-response",
                "echo-message",
                "message-tags",
                "server-time",
            ],
        )
        self.getMessages(qux)

        self.sendLine(
            bar,
            "@label=xyz;+example-client-tag=example-value PRIVMSG %s :hi there"
            % (qux,),
        )
        echo = self.getMessages(bar)[0]
        delivery = self.getMessages(qux)[0]

        self.assertEqual(delivery.params, [qux, "hi there"])
        self.assertEqual(delivery.params, echo.params)

        # Either both messages have a msgid, or neither does
        self.assertEqual(delivery.tags.get("msgid"), echo.tags.get("msgid"))

        self.assertEqual(
            echo.tags.get("label"),
            "xyz",
            fail_msg="expected message label 'xyz', but got {got!r}",
        )
        self.assertEqual(delivery.tags["+example-client-tag"], "example-value")
        self.assertEqual(
            delivery.tags["+example-client-tag"], echo.tags["+example-client-tag"]
        )


class EchoMessageTestCase(cases.BaseServerTestCase):
    def _testEchoMessage(command, solo, server_time):
        @cases.mark_capabilities("echo-message")
        def f(self):
            """<http://ircv3.net/specs/extensions/echo-message-3.2.html>"""
            self.addClient()
            self.sendLine(1, "CAP LS 302")
            capabilities = self.getCapLs(1)
            if "echo-message" not in capabilities:
                raise NotImplementedByController("echo-message")
            if server_time and "server-time" not in capabilities:
                raise NotImplementedByController("server-time")

            # TODO: check also without this
            self.sendLine(
                1,
                "CAP REQ :echo-message{}".format(" server-time" if server_time else ""),
            )
            self.getRegistrationMessage(1)
            # TODO: Remove this one the trailing space issue is fixed in Charybdis
            # and Mammon:
            # self.assertMessageEqual(m, command='CAP',
            #        params=['*', 'ACK', 'echo-message'] +
            #        (['server-time'] if server_time else []),
            #        fail_msg='Did not ACK advertised capabilities: {msg}')
            self.sendLine(1, "USER f * * :foo")
            self.sendLine(1, "NICK baz")
            self.sendLine(1, "CAP END")
            self.skipToWelcome(1)
            self.getMessages(1)

            self.sendLine(1, "JOIN #chan")

            if not solo:
                capabilities = ["server-time"] if server_time else None
                self.connectClient("qux", capabilities=capabilities)
                self.sendLine(2, "JOIN #chan")

            # Synchronize and clean
            self.getMessages(1)
            if not solo:
                self.getMessages(2)
                self.getMessages(1)

            self.sendLine(1, "{} #chan :hello everyone".format(command))
            m1 = self.getMessage(1)
            self.assertMessageEqual(
                m1,
                command=command,
                params=["#chan", "hello everyone"],
                fail_msg="Did not echo “{} #chan :hello everyone”: {msg}",
                extra_format=(command,),
            )

            if not solo:
                m2 = self.getMessage(2)
                self.assertMessageEqual(
                    m2,
                    command=command,
                    params=["#chan", "hello everyone"],
                    fail_msg="Did not propagate “{} #chan :hello everyone”: "
                    "after echoing it to the author: {msg}",
                    extra_format=(command,),
                )
                self.assertEqual(
                    m1.params,
                    m2.params,
                    fail_msg="Parameters of forwarded and echoed "
                    "messages differ: {} {}",
                    extra_format=(m1, m2),
                )
                if server_time:
                    self.assertIn(
                        "time",
                        m1.tags,
                        fail_msg="Echoed message is missing server time: {}",
                        extra_format=(m1,),
                    )
                    self.assertIn(
                        "time",
                        m2.tags,
                        fail_msg="Forwarded message is missing server time: {}",
                        extra_format=(m2,),
                    )

        return f

    testEchoMessagePrivmsgNoServerTime = _testEchoMessage("PRIVMSG", False, False)
    testEchoMessagePrivmsgSolo = _testEchoMessage("PRIVMSG", True, True)
    testEchoMessagePrivmsg = _testEchoMessage("PRIVMSG", False, True)
    testEchoMessageNotice = _testEchoMessage("NOTICE", False, True)
