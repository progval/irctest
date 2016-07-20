import ssl
import time
import socket
from .irc_utils import message_parser
from .exceptions import NoMessageException, ConnectionClosed

class ClientMock:
    def __init__(self, name, show_io):
        self.name = name
        self.show_io = show_io
        self.inbuffer = []
        self.ssl = False
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
    def starttls(self):
        assert not self.ssl, 'SSL already active.'
        self.conn = ssl.wrap_socket(self.conn)
        self.ssl = True
    def getMessages(self, synchronize=True, assert_get_one=False):
        if synchronize:
            token = 'synchronize{}'.format(time.monotonic())
            self.sendLine('PING {}'.format(token))
        got_pong = False
        data = b''
        (self.inbuffer, messages) = ([], self.inbuffer)
        conn = self.conn
        try:
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
                except ConnectionResetError:
                    raise ConnectionClosed()
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
                            print('{time:.3f}{ssl} S -> {client}: {line}'.format(
                                time=time.time(),
                                ssl=' (ssl)' if self.ssl else '',
                                client=self.name,
                                line=line))
                        message = message_parser.parse_message(line + '\r\n')
                        if message.command == 'PONG' and \
                                token in message.params:
                            got_pong = True
                        else:
                            messages.append(message)
                data = b''
        except ConnectionClosed:
            if messages:
                return messages
            else:
                raise
        else:
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
        if not line.endswith('\r\n'):
            line += '\r\n'
        encoded_line = line.encode()
        try:
            ret = self.conn.sendall(encoded_line)
        except BrokenPipeError:
            raise ConnectionClosed()
        if self.ssl: # https://bugs.python.org/issue25951
            assert ret == len(encoded_line), (ret, repr(encoded_line))
        else:
            assert ret is None, ret
        if self.show_io:
            print('{time:.3f}{ssl} {client} -> S: {line}'.format(
                time=time.time(),
                ssl=' (ssl)' if self.ssl else '',
                client=self.name,
                line=line.strip('\r\n')))
