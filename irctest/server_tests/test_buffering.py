"""Sends packets with various length to check the server reassembles them
correctly. Also checks truncation"""

import socket

from irctest import cases
from irctest.irc_utils import message_parser
from irctest.patma import ANYSTR


def _sendWhole(self, line):
    print("sending", repr(line.encode()))
    self.clients[1].conn.sendall(line.encode())


def _sendCharPerChar(self, line):
    print("sending", repr(line.encode()))
    for char in line:
        self.clients[1].conn.sendall(char.encode())


def _sendBytePerByte(self, line):
    print("sending", repr(line.encode()))
    for byte in line.encode():
        self.clients[1].conn.sendall(bytes([byte]))


def _testNoTags(sender_function, colon):
    def f(self):
        self.connectClient("foo")
        self.connectClient("bar")

        overhead = self.get_overhead(1, 2, colon=colon)
        print(f"overhead is {overhead}")

        line = f"PRIVMSG bar {colon}"
        remaining_size = 512 - len(line) - len("\r\n")
        emoji_size = len("😃".encode())
        payloads = [
            # one byte:
            "a",
            # one multi-byte char:
            "😃",
            # full payload, will be truncated
            "a" * remaining_size,
            "a" * (remaining_size - emoji_size) + "😃",
            # full payload to recipient:
            "a" * (remaining_size - overhead),
            "a" * (remaining_size - emoji_size - overhead) + "😃",
            # full payload to recipient plus one byte:
            "a" * (remaining_size - overhead + 1),
            "a" * (remaining_size - emoji_size - overhead + 1) + "😃",
            # full payload to recipient plus two bytes:
            "a" * (remaining_size - emoji_size - overhead + 1) + "😃",
        ]
        for payload in payloads:
            sender_function(self, line + payload + "\r\n")
            self.getMessages(1)

            received_line = self._getLine(2)
            print("received", repr(received_line))
            try:
                decoded_line = received_line.decode()
            except UnicodeDecodeError:
                # server truncated a byte off the emoji at the end
                if "UTF8ONLY" in self.server_support:
                    # https://github.com/ircv3/ircv3-specifications/pull/432
                    raise self.failureException(
                        f"Server advertizes UTF8ONLY, but sent an invalid UTF8 "
                        f"message: {received_line!r}"
                    )
                payload_intact = False
            else:
                msg = message_parser.parse_message(decoded_line)
                self.assertMessageMatch(msg, command="PRIVMSG", params=["bar", ANYSTR])
                payload_intact = msg.params[1] == payload
            if not payload_intact:
                # truncated
                self.assertLessEqual(len(received_line), 512, received_line)
                self.assertTrue(
                    payload.encode().startswith(
                        received_line.split(b" ")[-1].strip().lstrip(b":")
                    ),
                    f"expected payload to be a prefix of {payload!r}, "
                    f"but got {payload!r}",
                )

    return f


class BufferingTestCase(cases.BaseServerTestCase):
    # show_io = False

    def get_overhead(self, client1, client2, colon):
        self.sendLine(client1, f"PRIVMSG bar {colon}a\r\n")
        line = self._getLine(client2)
        return len(line) - len(f"PRIVMSG bar {colon}a\r\n")

    def _getLine(self, client) -> bytes:
        line = b""
        while True:
            try:
                data = self.clients[client].conn.recv(4096)
            except socket.timeout:
                data = b""
            line += data
            if not data or data.endswith(b"\r\n"):
                return line

    testNoTagsWholeNoColon = _testNoTags(_sendWhole, colon="")
    testNoTagsCharPerCharNoColon = _testNoTags(_sendCharPerChar, colon="")
    testNoTagsBytePerByteNoColon = _testNoTags(_sendBytePerByte, colon="")
    testNoTagsWholeColon = _testNoTags(_sendWhole, colon=":")
    testNoTagsCharPerCharColon = _testNoTags(_sendCharPerChar, colon=":")
    testNoTagsBytePerByteColon = _testNoTags(_sendBytePerByte, colon=":")
