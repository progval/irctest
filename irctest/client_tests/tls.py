"""Clients should validate certificates; either with a CA or fingerprints."""

import socket
import ssl

import pytest

from irctest import cases, runner, tls
from irctest.exceptions import ConnectionClosed
from irctest.patma import ANYSTR

BAD_CERT = """
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAOd2PGU3RNwhMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMTYwNzIwMDg0NjIwWhcNMTYwODE5MDg0NjIwWjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEAqo1Xu+f7UmdtNPTNPLxfILf9j/kGNNHkfqVjMHXc9rNL+JoMQ3eTdy7x
BqrWmiCHNOBAeES9anF+2SAd0LiOD2gO6h8R/+s9ftNCmZJa6kCGLX1uf5rp85aD
YbqbalgQS6PtRQZHU7+XOtW/YOolpG/2omgQmZMLyEQKNseQ4VQnuIYZoJRmXLsK
eyLgWNbpz0CsLljEziTsOLYnX9n8T469+EWgFQIvWpd/jirNTSPGTc3HVRs9g7dy
fZNi7b0jjb0qhDCOR0Kvyl9I0ANz4uEX+z/ZYfsZFU4xV7vxrDNp4gSAu8bW5JQy
/jJOsGL/9pXthCsXxY0S/6PQK70DOQIDAQABo1AwTjAdBgNVHQ4EFgQUME3YXimi
RNBg6V0SWY/417o/2zIwHwYDVR0jBBgwFoAUME3YXimiRNBg6V0SWY/417o/2zIw
DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAPljmzqGfc4wcdkTFSSBg
BQzq/nUn16cTtRYaOOxAxCK4VFWY9MxxlcVlDUx1VtUPBJaUNqJ+xdIIdwBOH3O/
jwDIQMRVlXwolTZvXw/xoatpb20644bltvftJ+6TpXY6z673+5Pu7b8FjNpZd/qs
5MGsgkAGkNN6hVvOqVASMqaO5vv7UgrL1Dh4R//ADBhonBwEP4Ykz+Y8gDVXlfSx
ak4YDQfuB2+M8Y3Y9PgKNZclYEacXwV/ZIxfm7vkOPlKOEeyi9+PzCEJINWnoE08
HNsJTz9ijzsHiac6Xw07FwOBQ/3LRngfcgEOqS6W8vTC4vCkWb88mbLI4CUwi+n7
dw==
-----END CERTIFICATE-----
"""
BAD_KEY = """
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCqjVe75/tSZ200
9M08vF8gt/2P+QY00eR+pWMwddz2s0v4mgxDd5N3LvEGqtaaIIc04EB4RL1qcX7Z
IB3QuI4PaA7qHxH/6z1+00KZklrqQIYtfW5/munzloNhuptqWBBLo+1FBkdTv5c6
1b9g6iWkb/aiaBCZkwvIRAo2x5DhVCe4hhmglGZcuwp7IuBY1unPQKwuWMTOJOw4
tidf2fxPjr34RaAVAi9al3+OKs1NI8ZNzcdVGz2Dt3J9k2LtvSONvSqEMI5HQq/K
X0jQA3Pi4Rf7P9lh+xkVTjFXu/GsM2niBIC7xtbklDL+Mk6wYv/2le2EKxfFjRL/
o9ArvQM5AgMBAAECggEAPwbqxDMvij1Uezx4WBiY4wN7fegeJgjm8vJ1nGQCG10Z
Fy7+lzQqV+IOClO56M1aiezRhmCIyzxUDzMyMX7yaLkgwd5njXbGjAbQVuZiGK1t
qIPxANEj4fPea5BFfOA8bWeP+HEgjM+BuKljBxKghIsnzs68S7SupvyV9bZ8UPho
uGZdgFfwzJlYTrjuZg1xz3KSsjDC/MrTQ3QldYlqMLjFooZH74j+vh/HAesEUu+E
aNMw0sAYi70F5xqAjLjEdNxKz05fGEkh1PPeohe2hF+vCDMMf/Si2PIbA44Z1Sod
0cFCE1zQhuJ1yOLQJwQ7wgEh9/Zz+M4L2BLB7P5OPQKBgQDgu1I1kqv/1EGTd36v
IQbYr1MVLzqWVXCTd7wdOcWIO538veQ/n/ED183I7xDt3GCBvXIwdoC0e4C9ZCAl
mjFUAawWDeQ0Ficbop51v1R/b/iAxQaIq1StUKrahZO0jjyH96CHISSUNlEWoRE3
Zh9F+PQ7tz77swn+q4oTeiUcBwKBgQDCSDVBZHO5mUTeVlyA+G93l/AwRxihWnGl
5yF/ybqxrf27MywhN7fhZCvNtcYfWTbJOh6fwnzcj0YcrPQFJ2QYt9R+tSLhkXPs
X5aXHH9MQ+lItUQ0rmSv2D8MpIulwmUpZIoCKMs17Pb81EU4NSFwa2eJmdezAyHW
T9LlQReWvwKBgDqbP0YvWOGftfZCLGx5fXKWzmDw7yNzZqdei1VH0qbDfWEDGHor
OMxaxBTJm62cUiKjiBrxXIE00A8UBHop6wFQalNaDhAzUsGXOCHW4q9VQQY724da
vvtv1Q6l1S46Bbkjr95tmz93ps/y8y1yWWeDFBZapHc5arrae2i26uSTAoGACEhf
zNvleyInp3rzEqSEzAp0OPqu+CIM+k+yQ+prxStvx81Usk3XzwogO/Ll8WwyQ73w
lEsMW7LYAFz3Qkj9oXgk3QoH5Kn40Tj6CJM0ciHrDih8MerFbCHB/l39fiGdgnhA
0fq/PxtNJFZAZTcOp+ZMUbd3VLBrfuGEUjXGNa0CgYEAqtwfoXxUIPWfZ7ezNX2m
Cbnl6JGjjYoDgohr8lHcpIc+dVChLopHayUxECWIU03Todlrn2/KNwjUKtovSsty
h4WuPDAI4yh24GjaCZYGR5xcqPCy5CNjMLxdA7HsP+Gcr3eY5XS7noBrbC6IaA0j
9E+dB63zMDFOnC4UVg5rD28=
-----END PRIVATE KEY-----
"""

GOOD_FINGERPRINT = "E1EE6DE2DBC0D43E3B60407B5EE389AEC9D2C53178E0FB14CD51C3DFD544AA2B"
GOOD_CERT = """
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKtD9XMC1R0vMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQwHhcNMTYwNzIwMDg0NjU0WhcNMTYwODE5MDg0NjU0WjBF
MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
CgKCAQEA0CZDv/ny3caI0a2r7P9qH3eyPYxd+Vz5i6YzCrVIqpq9PeWL9zf9IQoM
4TAOMS9VQOCq3HsSm0YKRC9tYflmBb03rriUExsFyd4CgAqKjYNJDrTWX23j+g5T
KHF+gYhQlIljQcvX1JVMHThS1nYCz6tnbBUsKrncW9LxnR0PydL+i8jS2SkPhe/z
t/VfWsTigSzz7xVEA54ow4sYbXVx1D6CNsjccTq/hfbRGkBWvYDZt7s/bj2h445Y
B1uVuIQygySkwGQMnNALZMUhiAsuCyV7PNNleGbIPUd0LExD6OQPVchof+tdiXq7
ndLsVv6Ufh1DhPDXtn9891sOkoj2cQIDAQABo1AwTjAdBgNVHQ4EFgQUtsTGgJ3E
rRxqF0doikKnpvDr/dswHwYDVR0jBBgwFoAUtsTGgJ3ErRxqF0doikKnpvDr/dsw
DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAWT2/0/ONY6XflNqGvn0i
XfB72FKIttuxMPiFKoV4czD2JWFZJ6eSTS+9NOUFPOzJfakl/F3a5Vy41hAF35o3
9N0jQt1ixkxi/BPEW2Twst4smnYgKHS4Lke8/EPn2gemxKEz7lpwICR/bFgOFIR5
OvQ2HQ+16yi8TsbB3QTUyVuixhYawlOpTtmDg9hho74+VA1oJ5bpx2maS2OTH35O
C458H4VAVNxtOIZF/zUhD8TEuTIElZtzJpghB9MdblaV8vs1fe2+ZWMXzSKOKj12
nGGz249IcunUMzjOzk6w7sVSZRWkwtwov5DsyaeW2+raig+NfF7sLECI57GWakVJ
Pg==
-----END CERTIFICATE-----
"""
GOOD_KEY = """
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDQJkO/+fLdxojR
ravs/2ofd7I9jF35XPmLpjMKtUiqmr095Yv3N/0hCgzhMA4xL1VA4KrcexKbRgpE
L21h+WYFvTeuuJQTGwXJ3gKACoqNg0kOtNZfbeP6DlMocX6BiFCUiWNBy9fUlUwd
OFLWdgLPq2dsFSwqudxb0vGdHQ/J0v6LyNLZKQ+F7/O39V9axOKBLPPvFUQDnijD
ixhtdXHUPoI2yNxxOr+F9tEaQFa9gNm3uz9uPaHjjlgHW5W4hDKDJKTAZAyc0Atk
xSGICy4LJXs802V4Zsg9R3QsTEPo5A9VyGh/612Jerud0uxW/pR+HUOE8Ne2f3z3
Ww6SiPZxAgMBAAECggEAMeb6lyv1bfYLFznr3gXeC21G7jqYzQ/dQ/20fvy3Ty+J
7yz5QWvK5ADk1ZgPzvrqFYPHctSOwWspSu+T6clBDF8w2lKmLW5tFNiFAO2GCidP
fJceTgKqhWipxyhui9+Cchn+Eegs9mpUtSyrr37bba5KPT9WN2gXzGvmQSSWhGwC
ewrJjh+HBpS3B006kqD9kOdgJYlmTayOaqD9WOH/ppFY8zNopEx27qqEph6WOA7W
84oUqm4JNabyXz7tRa/YsBUUqKmlBgxp0sKu5NttBPUi1+LpumjWIRj6M85NHliK
lCJgEkNriXMQ7joS0n0ZK+1cuKNr7hiGKwDoNUsfgQKBgQD0uB8KAgIjkgA+FRpr
cIQ35INPdkN8HkzZdg19nrQTwuh2Jo4SSbfm57KwyZBMnP2kHP6CMZNCycVXXj+r
1jo5ZFdAyz+MgUdTmTBXV/wH1YS6Cbp4KOv64eYT3/3cGUE5aBG0U5CqNaYq0XT7
CxPiF+pDRVDDQk+rBFz9gCKeWwKBgQDZvpd2DkVWvL0sk6pu9taPutKN145USzOn
j3SceLzL8Lu5nEfkW9O9EG0APVf8M7iq4JYF5Yzam94/pbLpSZHzYuEgNt1ee7TG
7cnxsKxQ9PDrvbElJGx0j0XRwG/CU3RJeDDmaUyosKjcYMhJujDk05Vm3RTLsii2
QiCvu4jwIwKBgQCXbl/2p2t/a1cvE4v3s/Z9R7BhuYLlCTLw1fZfJ5ezKscCZbVA
Z9Ge1v1iHDho0DS8Gxz6n4bKq2SsPawUv0nkPc0oUR0P6ueiOYcKZW2Vw3CQVnjG
5juwUZ0360GBszcDOPzLo3I/gVdD470Jo784Byh1XC0vxpbZ8qdATswdRQKBgDad
XXQZBD9LO8/QgfEvLIYEgAdfx61Q53Xhv4f3qLMmgI9/qXCXr7Y+RnjG6iix+GGz
zy1PdFLowYgJUaS99UOsy3a/DCtEsAUtY3ehrrbnmP4oKCR+zE04GnUP5XhCYmqD
IRDJ3JZ7KP+Nru7/KoBaqaCRV0P4PcnpMDWjvictAoGAWTFD2h/tsSWyHN2OyyBG
wmfusGVYB23RgQzXiLdlZOwWHZGON9dKEc9Pq6ddRArO01ewAKkcfieaLLpgb67C
Sw3oB/NsbUMkKze1zwXs9e2vcPt42vnRuQ75jU7Pb9p2NHpAdA4K/3CV00QzGA+e
El9iqRlAhgqaXc4Iz/Zxxhs=
-----END PRIVATE KEY-----
"""


class TlsTestCase(cases.BaseClientTestCase):
    def testTrustedCertificate(self):
        tls_config = tls.TlsConfig(enable=True, trusted_fingerprints=[GOOD_FINGERPRINT])
        (hostname, port) = self.server.getsockname()
        self.controller.run(
            hostname=hostname, port=port, auth=None, tls_config=tls_config
        )
        self.acceptClient(tls_cert=GOOD_CERT, tls_key=GOOD_KEY)
        self.getMessage()

    def testUntrustedCertificate(self):
        tls_config = tls.TlsConfig(enable=True, trusted_fingerprints=[GOOD_FINGERPRINT])
        (hostname, port) = self.server.getsockname()
        self.controller.run(
            hostname=hostname, port=port, auth=None, tls_config=tls_config
        )
        self.acceptClient(tls_cert=BAD_CERT, tls_key=BAD_KEY)
        with self.assertRaises((ConnectionClosed, ConnectionResetError)):
            self.getMessage()


class StsTestCase(cases.BaseClientTestCase):
    def setUp(self):
        super().setUp()
        self.insecure_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.insecure_server.bind(("", 0))  # Bind any free port
        self.insecure_server.listen(1)

    def tearDown(self):
        self.insecure_server.close()
        super().tearDown()

    @cases.mark_capabilities("sts")
    @pytest.mark.parametrize("portOnSecure", [False, True])
    def testSts(self, portOnSecure):
        if not self.controller.supports_sts:
            raise runner.CapabilityNotSupported("sts")
        tls_config = tls.TlsConfig(
            enable=False, trusted_fingerprints=[GOOD_FINGERPRINT]
        )

        # Connect client to insecure server
        (hostname, port) = self.insecure_server.getsockname()
        self.controller.run(
            hostname=hostname, port=port, auth=None, tls_config=tls_config
        )
        self.acceptClient(server=self.insecure_server)

        # Send STS policy to client
        self.assertMessageMatch(
            self.getMessage(),
            command="CAP",
            params=["LS", ANYSTR],
            fail_msg="First message is not CAP LS: {got}",
        )
        self.sendLine("CAP * LS :sts=port={}".format(self.server.getsockname()[1]))

        # "If the client is not already connected securely to the server
        # at the requested hostname, it MUST close the insecure connection
        # and reconnect securely on the stated port."
        self.acceptClient(tls_cert=GOOD_CERT, tls_key=GOOD_KEY)

        # Send the STS policy, over secure connection this time.
        if portOnSecure:
            # Should be ignored
            self.sendLine("CAP * LS :sts=duration=10,port=12345")
        else:
            self.sendLine("CAP * LS :sts=duration=10")

        # Make the client reconnect. It should reconnect to the secure server.
        self.sendLine("ERROR :closing link")
        self.acceptClient()

        # Kill the client
        self.controller.terminate()

        # Run the client, still configured to connect to the insecure server
        self.controller.run(
            hostname=hostname, port=port, auth=None, tls_config=tls_config
        )

        # The client should remember the STS policy and connect to the secure
        # server
        self.acceptClient()

    @cases.mark_capabilities("sts")
    def testStsInvalidCertificate(self):
        if not self.controller.supports_sts:
            raise runner.CapabilityNotSupported("sts")

        # Connect client to insecure server
        (hostname, port) = self.insecure_server.getsockname()
        self.controller.run(hostname=hostname, port=port, auth=None)
        self.acceptClient(server=self.insecure_server)

        # Send STS policy to client
        self.assertMessageMatch(
            self.getMessage(),
            command="CAP",
            params=["LS", ANYSTR],
            fail_msg="First message is not CAP LS: {got}",
        )
        self.sendLine("CAP * LS :sts=port={}".format(self.server.getsockname()[1]))

        # The client will reconnect to the TLS port. Unfortunately, it does
        # not trust its fingerprint.

        with self.assertRaises((ssl.SSLError, socket.error)):
            self.acceptClient(tls_cert=GOOD_CERT, tls_key=GOOD_KEY)
