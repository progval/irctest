"""
`Ergo <https://ergo.chat/>`_-specific tests for PROXY protocol support (v1 and v2).
"""

import socket
import struct

from irctest import cases
from irctest.numerics import RPL_WHOISACTUALLY


class ProxyProtocolTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Ergo")
    def test_proxy_v1(self):
        """Test that Ergo accepts a PROXY protocol v1 header as the first line
        from a connecting client and records the proxied IP as the client's
        apparent address, visible in RPL_WHOISACTUALLY (338)."""
        proxied_ip = "1.1.1.1"

        # Open a raw TCP connection without sending any IRC commands yet.
        client = self.addClient()

        # Send the PROXY protocol v1 header as the very first line.
        # Format: PROXY <proto> <src-ip> <dst-ip> <src-port> <dst-port>
        # The server accepts this because proxy-allowed-from includes localhost.
        self.sendLine(client, f"PROXY TCP4 {proxied_ip} 127.0.0.1 65533 6667")

        # Complete normal IRC registration.
        self.sendLine(client, "NICK proxyclient")
        self.sendLine(client, "USER proxy * * :Proxy Test User")
        self.skipToWelcome(client)
        self.getMessages(client)

        # WHOIS self to check the IP the server recorded for this connection.
        self.sendLine(client, "WHOIS proxyclient")
        whois_msgs = self.getMessages(client)

        # Ergo sends RPL_WHOISACTUALLY (338) with the real/proxied IP.
        actually_msgs = [m for m in whois_msgs if m.command == RPL_WHOISACTUALLY]
        self.assertNotEqual(
            actually_msgs,
            [],
            "Expected RPL_WHOISACTUALLY (338) in WHOIS response",
        )
        actually = actually_msgs[0]
        # Ergo's 338: <requester> <target> <user@host> <ip> :Actual user@host, Actual IP
        self.assertEqual(
            actually.params[3],
            proxied_ip,
            f"Expected proxied IP {proxied_ip!r} in RPL_WHOISACTUALLY params[3], "
            f"got: {actually.params!r}",
        )

    @cases.mark_specifications("Ergo")
    def test_proxy_v1_not_first_line(self):
        """Test that Ergo ignores a PROXY protocol v1 header that is not the
        very first line on the connection.  Any earlier IRC command disqualifies
        the PROXY line, so the proxied IP must not be recorded as the client's
        apparent address."""
        proxied_ip = "1.1.1.1"

        client = self.addClient()

        # Send NICK before PROXY so that PROXY is no longer the first line.
        self.sendLine(client, "NICK proxyclient2")
        self.sendLine(client, f"PROXY TCP4 {proxied_ip} 127.0.0.1 65533 6667")
        self.sendLine(client, "USER proxy * * :Proxy Test User")
        self.skipToWelcome(client)
        self.getMessages(client)

        self.sendLine(client, "WHOIS proxyclient2")
        whois_msgs = self.getMessages(client)

        actually_msgs = [m for m in whois_msgs if m.command == RPL_WHOISACTUALLY]
        self.assertNotEqual(
            actually_msgs,
            [],
            "Expected RPL_WHOISACTUALLY (338) in WHOIS response",
        )
        actually = actually_msgs[0]
        self.assertNotEqual(
            actually.params[3],
            proxied_ip,
            f"Server must not use the proxied IP {proxied_ip!r} when the PROXY "
            f"header was not the first line; got: {actually.params!r}",
        )


class ProxyProtocolV2TestCase(cases.BaseServerTestCase):
    @staticmethod
    def config() -> cases.TestCaseControllerConfig:
        def ergo_config(config: dict) -> None:
            for addr, conf in config["server"]["listeners"].items():
                if conf is None:
                    conf = {}
                conf["proxy"] = True
                config["server"]["listeners"][addr] = conf

        return cases.TestCaseControllerConfig(ergo_config=ergo_config)

    @cases.mark_specifications("Ergo")
    def test_proxy_v2(self):
        """Test that Ergo accepts a PROXY protocol v2 binary header as the
        first bytes on the connection and records the proxied IP as the
        client's apparent address, visible in RPL_WHOISACTUALLY (338).

        https://www.haproxy.org/download/1.8/doc/proxy-protocol.txt §2.2
        """
        proxied_ip = "1.1.1.1"

        # Build the PROXY v2 binary header for a TCP/IPv4 connection.
        #
        # Fixed 12-byte signature
        # version+command: 0x21 = version 2, command PROXY (1)
        # family+protocol: 0x11 = AF_INET (1), STREAM/TCP (1)
        # length:          0x000C = 12 bytes of address data follow
        # address data:    src-ip (4) dst-ip (4) src-port (2) dst-port (2)
        header = (
            b"\x0D\x0A\x0D\x0A\x00\x0D\x0A\x51\x55\x49\x54\x0A"  # signature
            b"\x21"  # version 2 | command PROXY
            b"\x11"  # AF_INET   | STREAM (TCP4)
            b"\x00\x0C"  # address block length = 12 bytes
        )
        header += socket.inet_aton(proxied_ip)  # source address
        header += socket.inet_aton("127.0.0.1")  # destination address
        header += struct.pack("!HH", 65533, 6667)  # source port, dest port

        client = self.addClient()
        # Send the binary header directly; sendLine would append CRLF and
        # corrupt the fixed-length binary structure.
        self.clients[client].conn.sendall(header)

        self.sendLine(client, "NICK proxyclientv2")
        self.sendLine(client, "USER proxy * * :Proxy Test User")
        self.skipToWelcome(client)
        self.getMessages(client)

        self.sendLine(client, "WHOIS proxyclientv2")
        whois_msgs = self.getMessages(client)

        actually_msgs = [m for m in whois_msgs if m.command == RPL_WHOISACTUALLY]
        self.assertNotEqual(
            actually_msgs,
            [],
            "Expected RPL_WHOISACTUALLY (338) in WHOIS response",
        )
        actually = actually_msgs[0]
        self.assertEqual(
            actually.params[3],
            proxied_ip,
            f"Expected proxied IP {proxied_ip!r} in RPL_WHOISACTUALLY params[3], "
            f"got: {actually.params!r}",
        )
