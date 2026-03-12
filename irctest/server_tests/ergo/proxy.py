"""
`Ergo <https://ergo.chat/>`_-specific tests for PROXY protocol support (v1 and v2).
"""

import socket
import struct

from irctest import cases
from irctest.numerics import RPL_WHOISACTUALLY


def get_whoisactually_ip(test_case, whois_msgs):
    actually_msgs = [m for m in whois_msgs if m.command == RPL_WHOISACTUALLY]
    test_case.assertEqual(
        len(actually_msgs),
        1,
        "Expected exactly 1 RPL_WHOISACTUALLY (338) in WHOIS response",
    )
    # RPL_WHOISACTUALLY: <requester> <target> <user@host> <ip> :Actual user@host, Actual IP
    return actually_msgs[0].params[3]


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
        effective_ip = get_whoisactually_ip(self, whois_msgs)
        self.assertEqual(
            effective_ip, proxied_ip, "Proxied IP was not applied successfully"
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
        effective_ip = get_whoisactually_ip(self, whois_msgs)
        self.assertNotEqual(
            effective_ip,
            proxied_ip,
            "Proxied IP was applied successfully, but should not have been",
        )


class ProxyProtocolListenerTestCase(cases.BaseServerTestCase):
    """Test Ergo's support for `proxy: true` in listener configuration,
    which requires that a PROXY header (either v1 or v2) be sent ahead
    of the connection data.
    """

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
    def test_proxy_v1(self):
        """Test that Ergo accepts a PROXY protocol v1 ASCII header as the
        first bytes on the connection and records the proxied IP as the
        client's apparent address, visible in RPL_WHOISACTUALLY (338).
        """
        proxied_ip = "1.1.1.1"

        # Open a raw TCP connection without sending any IRC commands yet.
        client = self.addClient()
        # Send PROXY v1 (ASCII) header as first line.
        self.sendLine(client, f"PROXY TCP4 {proxied_ip} 127.0.0.1 65533 6667")

        # Complete normal IRC registration.
        self.sendLine(client, "NICK proxyclient")
        self.sendLine(client, "USER proxy * * :Proxy Test User")
        self.skipToWelcome(client)
        self.getMessages(client)

        # WHOIS self to check the IP the server recorded for this connection.
        self.sendLine(client, "WHOIS proxyclient")
        whois_msgs = self.getMessages(client)
        effective_ip = get_whoisactually_ip(self, whois_msgs)
        self.assertEqual(
            effective_ip, proxied_ip, "Proxied IP was not applied successfully"
        )

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
            b"\r\n\r\n\x00\r\nQUIT\n"  # signature
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
        effective_ip = get_whoisactually_ip(self, whois_msgs)
        self.assertEqual(
            effective_ip, proxied_ip, "Proxied IP was not applied successfully"
        )

    @cases.mark_specifications("Ergo")
    def test_no_proxy_header(self):
        """Test if a listener is configured with `proxy: true`,
        connections that do not send a valid proxy header are rejected.
        """
        client = self.addClient()
        self.sendLine(client, "NICK proxyclient")
        self.assertDisconnected(client)
