import socket
import ssl
import sys
import time
from typing import Any, Callable, List, Optional, Union

from .exceptions import ConnectionClosed, NoMessageException
from .irc_utils import message_parser


class ClientMock:
    def __init__(self, name: Any, show_io: bool):
        self.name = name
        self.show_io = show_io
        self.inbuffer: List[message_parser.Message] = []
        self.ssl = False

    def connect(self, hostname: str, port: int) -> None:
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(1)  # TODO: configurable
        self.conn.connect((hostname, port))
        if self.show_io:
            print("{:.3f} {}: connects to server.".format(time.time(), self.name))

    def disconnect(self) -> None:
        if self.show_io:
            print("{:.3f} {}: disconnects from server.".format(time.time(), self.name))
        self.conn.close()

    def starttls(self) -> None:
        assert not self.ssl, "SSL already active."
        self.conn = ssl.wrap_socket(self.conn)
        self.ssl = True

    def getMessages(
        self, synchronize: bool = True, assert_get_one: bool = False, raw: bool = False
    ) -> List[message_parser.Message]:
        """actually returns List[str] in the rare case where raw=True."""
        token: Optional[str]
        if synchronize:
            token = "synchronize{}".format(time.monotonic())
            self.sendLine("PING {}".format(token))
        else:
            token = None
        got_pong = False
        data = b""
        (self.inbuffer, messages) = ([], self.inbuffer)
        conn = self.conn
        try:
            while not got_pong:
                try:
                    new_data = conn.recv(4096)
                except socket.timeout:
                    if not assert_get_one and not synchronize and data == b"":
                        # Received nothing
                        return []
                    if self.show_io:
                        print("{:.3f} {}: waiting…".format(time.time(), self.name))
                    continue
                except ConnectionResetError:
                    raise ConnectionClosed()
                else:
                    if not new_data:
                        # Connection closed
                        raise ConnectionClosed()
                data += new_data
                if not new_data.endswith(b"\r\n"):
                    continue
                if not synchronize:
                    got_pong = True
                for line in data.decode().split("\r\n"):
                    if line:
                        if self.show_io:
                            print(
                                "{time:.3f}{ssl} S -> {client}: {line}".format(
                                    time=time.time(),
                                    ssl=" (ssl)" if self.ssl else "",
                                    client=self.name,
                                    line=line,
                                )
                            )
                        message = message_parser.parse_message(line)
                        if message.command == "PONG" and token in message.params:
                            got_pong = True
                        else:
                            if raw:
                                messages.append(line)  # type: ignore
                            else:
                                messages.append(message)
                data = b""
        except ConnectionClosed:
            if messages:
                return messages
            else:
                raise
        else:
            return messages

    def getMessage(
        self,
        filter_pred: Optional[Callable[[message_parser.Message], bool]] = None,
        synchronize: bool = True,
        raw: bool = False,
    ) -> message_parser.Message:
        """Returns str in the rare case where raw=True"""
        while True:
            if not self.inbuffer:
                self.inbuffer = self.getMessages(
                    synchronize=synchronize, assert_get_one=True, raw=raw
                )
            if not self.inbuffer:
                raise NoMessageException()
            message = self.inbuffer.pop(0)  # TODO: use dequeue
            if not filter_pred or filter_pred(message):
                return message

    def sendLine(self, line: Union[str, bytes]) -> None:
        if isinstance(line, str):
            encoded_line = line.encode()
        elif isinstance(line, bytes):
            encoded_line = line
        else:
            raise ValueError(line)
        if not encoded_line.endswith(b"\r\n"):
            encoded_line += b"\r\n"
        try:
            ret = self.conn.sendall(encoded_line)  # type: ignore
        except BrokenPipeError:
            raise ConnectionClosed()
        if (
            sys.version_info <= (3, 6) and self.ssl
        ):  # https://bugs.python.org/issue25951
            assert ret == len(encoded_line), (ret, repr(encoded_line))
        else:
            assert ret is None, ret
        if self.show_io:
            if isinstance(line, str):
                escaped_line = line
                escaped = ""
            else:
                escaped_line = repr(line)
                escaped = " (escaped)"
            print(
                "{time:.3f}{escaped}{ssl} {client} -> S: {line}".format(
                    time=time.time(),
                    escaped=escaped,
                    ssl=" (ssl)" if self.ssl else "",
                    client=self.name,
                    line=escaped_line.strip("\r\n"),
                )
            )
