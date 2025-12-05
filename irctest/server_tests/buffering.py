"""
Sends packets with various length to check the server reassembles them
correctly. Also checks truncation.
"""

import socket
import time

import pytest

from irctest import cases
from irctest.irc_utils import message_parser
from irctest.numerics import ERR_INPUTTOOLONG
from irctest.patma import ANYSTR


def _sendWhole(self, line):
    print("(repr) 1 -> S", repr(line.encode()))
    self.clients[1].conn.sendall(line.encode())


def _sendCharPerChar(self, line):
    print("(repr) 1 -> S", repr(line.encode()))
    for char in line:
        self.clients[1].conn.sendall(char.encode())


def _sendBytePerByte(self, line):
    print("(repr) 1 -> S", repr(line.encode()))
    for byte in line.encode():
        self.clients[1].conn.sendall(bytes([byte]))


class BufferingTestCase(cases.BaseServerTestCase):
    @cases.xfailIfSoftware(
        ["Bahamut"],
        "cannot pass because of issues with UTF-8 handling: "
        "https://github.com/DALnet/bahamut/issues/196",
    )
    @cases.xfailIfSoftware(
        ["ircu2", "Nefarious", "snircd"],
        "ircu2 discards the whole buffer on long lines "
        "(TODO: refine how we exclude these tests)",
    )
    @pytest.mark.parametrize(
        "sender_function,colon",
        [
            pytest.param(_sendWhole, "", id="whole-no colon"),
            pytest.param(_sendCharPerChar, "", id="charperchar-no colon"),
            pytest.param(_sendBytePerByte, "", id="byteperbyte-no colon"),
            pytest.param(_sendWhole, ":", id="whole-colon"),
            pytest.param(_sendCharPerChar, ":", id="charperchar-colon"),
            pytest.param(_sendBytePerByte, ":", id="byteperbyte-colon"),
        ],
    )
    def testNoTags(self, sender_function, colon):
        self.connectClient("nick1")
        self.connectClient("nick2")

        overhead = self.get_overhead(1, 2, colon=colon)
        print(f"overhead is {overhead}")

        line = f"PRIVMSG nick2 {colon}"
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
            messages = self.getMessages(1)
            if messages and ERR_INPUTTOOLONG in (m.command for m in messages):
                # https://defs.ircdocs.horse/defs/numerics.html#err-inputtoolong-417
                self.assertGreater(
                    len((line + payload + "\r\n").encode()),
                    512 - overhead,
                    "Got ERR_INPUTTOOLONG for a message that should fit "
                    "within 512 characters.",
                )
                continue

            received_line = self._getLine(2)
            print("(repr) S -> 2", repr(received_line))
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
                msg = message_parser.parse_message(decoded_line[:-2])
                self.assertMessageMatch(
                    msg, command="PRIVMSG", params=["nick2", ANYSTR]
                )
                payload_intact = msg.params[1] == payload
            if not payload_intact:
                # truncated
                self.assertLessEqual(len(received_line), 512, received_line)
                if received_line.endswith(b"[CUT]\r\n"):
                    # ngircd
                    received_line = received_line[0:-7] + b"\r\n"
                self.assertTrue(
                    payload.encode().startswith(
                        received_line.split(b" ")[-1].strip().lstrip(b":")
                    ),
                    f"expected payload to be a prefix of {payload!r}, "
                    f"but got {payload!r}",
                )
            if self.controller.software_name == "Ergo":
                self.assertTrue(
                    payload_intact,
                    f"Ergo should not truncate messages: {repr(line + payload)}, {repr(received_line)}",
                )

    def get_overhead(self, client1, client2, colon):
        """Compute the overhead added to client1's message:
                          PRIVMSG nick2 a\r\n
        :nick1!~user@host PRIVMSG nick2 :a\r\n
        So typically client1's NUH length plus either 2 or 3 bytes
        (the initial colon, the space between source and command, and possibly
        a colon preceding the trailing).
        """
        outgoing = f"PRIVMSG nick2 {colon}a\r\n"
        self.sendLine(client1, outgoing)
        line = self._getLine(client2)
        return len(line) - len(outgoing.encode())

    def _getLine(self, client) -> bytes:
        line = b""
        for _ in range(30):
            try:
                data = self.clients[client].conn.recv(4096)
            except socket.timeout:
                data = b""
            line += data
            if line.endswith(b"\r\n"):
                return line
            time.sleep(0.1)
            print(f"{client}: Waiting...")
        raise ValueError(f"Received unterminated line: {repr(line)}")
