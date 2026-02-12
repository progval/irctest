"""
`IRCv3 websocket transport <https://ircv3.net/specs/extensions/websocket>`_
"""

import time
from typing import List, Optional, Union

import pytest

try:
    from websockets.sync.client import ClientConnection, connect
except ImportError:
    connect = None

from irctest import cases
from irctest.client_mock import ClientMock
from irctest.irc_utils import message_parser
from irctest.patma import StrRe


class WebClientMock(ClientMock):
    conn: ClientConnection

    def __init__(self, *, subprotocols: List[str], binary: bool, **kwargs):
        super().__init__(**kwargs)
        self.subprotocols = subprotocols
        self.binary = binary

    def connect(self, url):
        started_at = time.time()
        while True:
            try:
                self.conn = connect(url, subprotocols=self.subprotocols)
            except ConnectionRefusedError:
                print(f"{url} connection refused")
                if time.time() - started_at >= 60:
                    # waited for 60 seconds, giving up
                    raise
                time.sleep(0.1)
            else:
                break

        if self.show_io:
            print(
                "{:.3f} {}: connects to server with websocket (requested subprotocols: {}, negotiated: {}).".format(
                    time.time(), self.name, self.subprotocols, self.conn.subprotocol
                )
            )

    def disconnect(self) -> None:
        if self.show_io:
            print(
                "{:.3f} {}: disconnects from server with websocket.".format(
                    time.time(), self.name
                )
            )
        self.conn.close()

    def getMessages(
        self,
        synchronize: bool = True,
        assert_get_one: bool = False,
        raw: bool = False,
        **kwargs,
    ) -> List[message_parser.Message]:
        token: Optional[str]
        if synchronize:
            token = "synchronize{}".format(time.monotonic())
            self.sendLine("PING {}".format(token))
        else:
            token = None

        got_pong = False
        messages: List[message_parser.Message] = []
        while not got_pong:
            try:
                line = self.conn.recv(timeout=self.socket_timeout, **kwargs)
            except TimeoutError:
                if (messages or not assert_get_one) and not synchronize:
                    # Received nothing
                    return messages
                if self.show_io:
                    print("{:.3f} {}: waiting…".format(time.time(), self.name))
                continue
            self.logReceivedLine(line)
            if self.binary:
                try:
                    decoded_line = line.decode()
                except UnicodeDecodeError:
                    print(
                        "{time:.3f} (websocket) S -> {client} - failed to decode: {line!r}".format(
                            time=time.time(),
                            client=self.name,
                            line=line,
                        )
                    )
                    raise
            else:
                decoded_line = line
            message = message_parser.parse_message(decoded_line)

            if message.command == "PONG" and token in message.params:
                return messages
            elif (
                synchronize and message.command == "451" and message.params[1] == "PING"
            ):
                raise ValueError("Got '451 * PONG'. Did you forget synchronize=False?")
            if raw:
                messages.append(line)  # type: ignore
            else:
                messages.append(message)

        return messages

    def sendLine(self, line: Union[str, bytes], **kwargs) -> None:
        if self.binary and isinstance(line, str):
            line = line.encode()
        elif not self.binary and isinstance(line, bytes):
            line = line.decode()
        self.conn.send(line)
        self.logSentLine(line)

    def logSuffix(self) -> str:
        return " (websocket)"


class WebsocketTestCase(cases.BaseServerTestCase):
    websocket = True

    def addClient(self, name: Optional[int], websocket: bool, **kwargs) -> int:  # type: ignore[override]
        if websocket:
            assert self.websocket_url
            # don't wait for port, assume we already connected a non-web client

            if not name:
                used_ids: List[int] = [
                    int(name) for name in self.clients if isinstance(name, (int, str))
                ]
                new_name = max(used_ids + [0]) + 1
                name = int(new_name)
            self.clients[name] = client = WebClientMock(
                name=name, show_io=True, **kwargs
            )
            client.connect(self.websocket_url)

            return name
        else:
            return super().addClient(name=name, **kwargs)  # type: ignore[no-any-return]

    @pytest.mark.parametrize(
        "offered_subprotocols,expected_subprotocol,binary",
        [
            pytest.param(
                ["binary.ircv3.net"], "binary.ircv3.net", True, id="binary-only"
            ),
            pytest.param(["text.ircv3.net"], "text.ircv3.net", False, id="text-only"),
            pytest.param(
                ["binary.ircv3.net", "text.ircv3.net"],
                "binary.ircv3.net",
                True,
                id="binary-first",
            ),
            pytest.param(
                ["text.ircv3.net", "binary.ircv3.net"],
                "text.ircv3.net",
                False,
                id="text-first",
            ),
        ],
    )
    def testSubprotocolNegotiation(
        self, offered_subprotocols, expected_subprotocol, binary
    ):
        self.connectClient("nonweb", websocket=False)
        self.connectClient(
            "web", websocket=True, subprotocols=offered_subprotocols, binary=binary
        )

        self.assertEqual(self.clients[2].conn.subprotocol, expected_subprotocol)

        self.sendLine(2, "PRIVMSG nonweb :hello")
        self.assertMessageMatch(
            self.getMessage(1),
            command="PRIVMSG",
            params=["nonweb", "hello"],
            prefix=StrRe("web!.*@.*"),
        )

        self.sendLine(1, "PRIVMSG web :hi")
        self.assertMessageMatch(
            self.getMessage(2),
            command="PRIVMSG",
            params=["web", "hi"],
            prefix=StrRe("nonweb!.*@.*"),
        )

    def testSendNonUtf8Text(self):
        self.connectClient("nonweb", websocket=False)
        self.connectClient(
            "web", websocket=True, subprotocols=["text.ircv3.net"], binary=False
        )

        self.clients[
            2
        ].binary = True  # force the websocket library to send a binary message
        self.sendLine(2, b"PRIVMSG nonweb :caf\xe9")
        self.clients[2].binary = False
        self.getMessages(2)
        # TODO: check we did not get an error back

        # if the server accepted the binary message (even though the spec does not explicitly allow it),
        # make sure it successfully sent it to other clients.

        line = self.clients[1].conn.recv(4096)
        print(
            "{time:.3f} S -> 1: {data!r}".format(
                time=time.time(),
                data=line,
            )
        )
        line = line.removesuffix(b"\r\n")

        # naive tests on bytes
        (*_, command, target, payload) = line.rsplit(b" ")
        self.assertEqual(command, b"PRIVMSG", line)
        self.assertEqual(target, b"nonweb", line)
        self.assertEqual(payload, b":caf\xe9", line)

        # test after correct parsing
        self.assertMessageMatch(
            message_parser.parse_message(line.decode("latin1")),
            command="PRIVMSG",
            params=["nonweb", "café"],
            prefix=StrRe("web!.*@.*"),
        )

    def testReceiveNonUtf8Text(self):
        self.connectClient("nonweb", websocket=False)

        self.connectClient(
            "web", websocket=True, subprotocols=["text.ircv3.net"], binary=False
        )

        self.sendLine(1, b"PRIVMSG web :caf\xe9")
        self.getMessages(1)
        # TODO: check we did not get an error back

        line = self.getMessage(2, raw=True)
        self.assertTrue(isinstance(line, str), f"Expected text message, got {line!r}")

        # naive tests just to be safe
        (*_, command, target, payload) = line.rsplit(" ")
        self.assertEqual(command, "PRIVMSG", line)
        self.assertEqual(target, "web", line)
        self.assertEqual(payload, ":caf\N{REPLACEMENT CHARACTER}", line)

        # test after correct parsing
        self.assertMessageMatch(
            message_parser.parse_message(line),
            command="PRIVMSG",
            params=["web", "caf\N{REPLACEMENT CHARACTER}"],
            prefix=StrRe("nonweb!.*@.*"),
        )
