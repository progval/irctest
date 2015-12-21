import time
import socket
from .irc_utils import message_parser


class NoMessageException(AssertionError):
    pass

class ConnectionClosed(Exception):
    pass

class ClientMock:
    def __init__(self, name, show_io):
        self.name = name
        self.show_io = show_io
        self.inbuffer = []
    def connect(self, hostname, port):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.settimeout(1) # TODO: configurable
        self.conn.connect((hostname, port))
        if self.show_io:
            print('{:.3f} {}: connects to server.'.format(time.time(), self.name))
    def disconnect(self):
        if self.show_io:
            print('{:.3f} {}: disconnects from server.'.format(time.time(), self.name))
        self.conn.close()
    def getMessages(self, synchronize=True, assert_get_one=False):
        if synchronize:
            token = 'synchronize{}'.format(time.monotonic())
            self.sendLine('PING {}'.format(token))
        got_pong = False
        data = b''
        messages = []
        conn = self.conn
        while not got_pong:
            try:
                new_data = conn.recv(4096)
            except socket.timeout:
                if not assert_get_one and not synchronize and data == b'':
                    # Received nothing
                    return []
                if self.show_io:
                    print('{:.3f} waiting…'.format(time.time()))
                time.sleep(0.1)
                continue
            else:
                if not new_data:
                    # Connection closed
                    raise ConnectionClosed()
            data += new_data
            if not new_data.endswith(b'\r\n'):
                time.sleep(0.1)
                continue
            if not synchronize:
                got_pong = True
            for line in data.decode().split('\r\n'):
                if line:
                    if self.show_io:
                        print('{:.3f} S -> {}: {}'.format(time.time(), self.name, line.strip()))
                    message = message_parser.parse_message(line + '\r\n')
                    if message.command == 'PONG' and \
                            token in message.params:
                        got_pong = True
                    else:
                        messages.append(message)
            data = b''
        return messages
    def getMessage(self, filter_pred=None, synchronize=True):
        while True:
            if not self.inbuffer:
                self.inbuffer = self.getMessages(
                        synchronize=synchronize, assert_get_one=True)
            if not self.inbuffer:
                raise NoMessageException()
            message = self.inbuffer.pop(0) # TODO: use dequeue
            if not filter_pred or filter_pred(message):
                return message
    def sendLine(self, line):
        ret = self.conn.sendall(line.encode())
        assert ret is None
        if not line.endswith('\r\n'):
            ret = self.conn.sendall(b'\r\n')
            assert ret is None
        if self.show_io:
            print('{:.3f} {} -> S: {}'.format(time.time(), self.name, line.strip()))
