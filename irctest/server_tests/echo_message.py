"""
`IRCv3 echo-message <https://ircv3.net/specs/extensions/echo-message>`_
"""

import pytest

from irctest import cases
from irctest.irc_utils.junkdrawer import random_name
from irctest.patma import ANYDICT


class EchoMessageTestCase(cases.BaseServerTestCase):
    @pytest.mark.parametrize(
        "command,solo,server_time",
        [
            ("PRIVMSG", False, False),
            ("PRIVMSG", True, True),
            ("PRIVMSG", False, True),
            ("NOTICE", False, True),
        ],
    )
    @cases.mark_capabilities("echo-message")
    def testEchoMessage(self, command, solo, server_time):
        """<http://ircv3.net/specs/extensions/echo-message-3.2.html>"""
        capabilities = ["server-time"] if server_time else []

        self.connectClient(
            "baz",
            capabilities=["echo-message", *capabilities],
            skip_if_cap_nak=True,
        )

        self.sendLine(1, "JOIN #chan")

        # Synchronize
        self.getMessages(1)

        if not solo:
            self.connectClient("qux", capabilities=capabilities)
            self.sendLine(2, "JOIN #chan")

        # Synchronize and clean
        self.getMessages(1)
        if not solo:
            self.getMessages(2)
            self.getMessages(1)

        self.sendLine(1, "{} #chan :hello everyone".format(command))
        m1 = self.getMessage(1)
        self.assertMessageMatch(
            m1,
            command=command,
            params=["#chan", "hello everyone"],
            fail_msg="Did not echo “{} #chan :hello everyone”: {msg}",
            extra_format=(command,),
        )

        if not solo:
            m2 = self.getMessage(2)
            self.assertMessageMatch(
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
                fail_msg="Parameters of forwarded and echoed " "messages differ: {} {}",
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

    @pytest.mark.arbitrary_client_tags
    @cases.mark_capabilities(
        "batch", "labeled-response", "echo-message", "message-tags"
    )
    def testDirectMessageEcho(self):
        bar = random_name("bar")
        self.connectClient(
            bar,
            name=bar,
            capabilities=["batch", "labeled-response", "echo-message", "message-tags"],
            skip_if_cap_nak=True,
        )
        self.getMessages(bar)

        qux = random_name("qux")
        self.connectClient(
            qux,
            name=qux,
            capabilities=["batch", "labeled-response", "echo-message", "message-tags"],
        )
        self.getMessages(qux)

        self.sendLine(
            bar,
            "@label=xyz;+example-client-tag=example-value PRIVMSG %s :hi there"
            % (qux,),
        )
        echo = self.getMessages(bar)[0]
        delivery = self.getMessages(qux)[0]

        self.assertMessageMatch(
            echo,
            command="PRIVMSG",
            params=[qux, "hi there"],
            tags={"label": "xyz", "+example-client-tag": "example-value", **ANYDICT},
        )
        self.assertMessageMatch(
            delivery,
            command="PRIVMSG",
            params=[qux, "hi there"],
            tags={"+example-client-tag": "example-value", **ANYDICT},
        )

        # Either both messages have a msgid, or neither does
        self.assertEqual(delivery.tags.get("msgid"), echo.tags.get("msgid"))
