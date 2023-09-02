import os
import shutil
import signal
import subprocess
from typing import Optional, Type

from irctest.basecontrollers import (
    BaseServerController,
    BaseServicesController,
    DirectoryBasedController,
    NotImplementedByController,
)

CA_CERT = """
-----BEGIN CERTIFICATE-----
MIIFTzCCAzegAwIBAgIUeZftWHZt/EynCscf0WivCZrvJQgwDQYJKoZIhvcNAQEL
BQAwNzELMAkGA1UEBhMCR0IxCjAIBgNVBAgMASAxCjAIBgNVBAoMASAxEDAOBgNV
BAMMB1Rlc3QgQ0EwHhcNMjExMTI3MTgzNDM5WhcNMjExMjI3MTgzNDM5WjA3MQsw
CQYDVQQGEwJHQjEKMAgGA1UECAwBIDEKMAgGA1UECgwBIDEQMA4GA1UEAwwHVGVz
dCBDQTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAMiaSa7TqdkMy0ZB
CsL79yVklDoePTXLiqKKpfv8buvor+xM2qj5c8sPIlPQTwk6xPWD9Cy6kvpfHUSG
cPvBgHtoJBiGBST36fFU5jwof5ZGK12zYWNjTuG6j85da/JbuD9+5/GlMjbII3Vy
Aky74eM7OjX07AgjQp0VBTCsQ711fgKqfzQKEePBQipxeyFoa3yrwrU9gKfwYR3g
GswpWqkVHktqPVXIpO9tVzFYW4uSq/79HUhNDCZceAHuqg4JLUDhrpvkGiCSFGPd
PzzNd314cFihtfD6fxXikR7zMnHQOdckiFM2/bZlxl75Qmt9OxUNAUv1kP+JGJkh
7Id9gRPG3I96cjva/mXuYIwTAE7hAFulfZE2d2PNh8dlka9luUpp5/EBR2S8vsGl
y+Py67jB+KdASto8pZuEHGBEaLeVHIgUuBCPyUvRT+cBGwH4QNPJ9laW6778q0RI
TZDI1+O8A3Lo3aO1PA+bF4tZuWDL3FtNIJwBsNqgN0ieS48tqlZm51xlA/ddeolQ
O3zjDgxBAq2ymp2QcRHMWhrHlxWAUnPXyqMiPt1QutII0xooyp+6/EFxtKnEFY4C
3/JosSNox5D5J+fl29b/YHHW7SSj9BKQP+cwtdD/6VtcMsErO11LiDudSGttxy+q
ZTEdikLmSA1ai1Q/afmXmm5kuNQBAgMBAAGjUzBRMB0GA1UdDgQWBBRZegm42rfb
5AmC9XkqVLjG5nsbCjAfBgNVHSMEGDAWgBRZegm42rfb5AmC9XkqVLjG5nsbCjAP
BgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4ICAQCSrNHP9ITBGh8hMRXH
Yy0XmDMvwG5Z2eUm+2092b3RoU/pm7bIU+bDH9yfY+JV1Z0CCOu2bGz/Uj+c4j/Q
0Jqck4xvxGnJUzQQxQ4wHdabWWXq2PZDv84lzJela5dpI1u+zSJqbRbYz2tkFhj9
nIz4GZ9u8aYBGe2pvVK6mjd1Y8QlE9zk4MJkz/ngr4c/CnbmcqegJw7neZuRxAlR
FK75Db4mn3UNXW+gioiTTFxaHFeAC5ymIsXRmdeubqetZPZr/PY644hnfYP0kzPB
jnokeUBO1isXya65NMMFPKlhd1b5x3rLkueBcg/zK4CXwweqq9RhqLJf27UuClvB
wrDwb+P4RO2caIrk9B6iR9V4gh7HwgLTrf5W+aljKl5D0K3ixCzO1XxH9u5TN+61
vbVAsiILbjLAE9Bq27iSiRoORIbQUTt7qygVh28cbKJmPHaXJXMPn+X4WQhNhoo3
Ac29CLjy63I/pDQJuVsqb4U5ttU0vdZU939Fc6fnsd+QlGLZOn4M0t/w1G+6mLj9
n85Ry+jLFvaNhaBKczLGs2JNC7JOUT7xXVPdVi/JbvIq8ZlipPTzxCvONYJaPc8A
UBjRIFdhNHVPAwMDksOKweFVLHxYyqwBRiNdeK7tDpYNe2X17BGarK4nm8ubqq7+
dPOg3zrzrtNOYVg4jnRqLwNTDQ==
-----END CERTIFICATE-----
"""

SERVER_KEY = """
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
"""

SERVER_CERT = """
-----BEGIN CERTIFICATE-----
MIIFFjCCAv6gAwIBAgICEAswDQYJKoZIhvcNAQELBQAwNzELMAkGA1UEBhMCR0Ix
CjAIBgNVBAgMASAxCjAIBgNVBAoMASAxEDAOBgNVBAMMB1Rlc3QgQ0EwHhcNMjIx
MjAxMTUxMjQzWhcNMjMxMjAxMTUxMjQzWjBIMQswCQYDVQQGEwJHQjEKMAgGA1UE
CAwBIDEKMAgGA1UECgwBIDEKMAgGA1UECwwBIDEVMBMGA1UEAwwMc2VydmVyMS50
ZXN0MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAwQ2J3F7sRNYnuypW
mOkCUCBX9xpj9xIZptCFPuGdhUCBoe06tz5nBP6tPJphw0rVTaH9g6nWXg3Z+Q3a
okl5duC9AOxtxUn+wa8zcJhmwAky54nDWyXkVgzmN0pZK/1k2AZQG2vEdfe1sVX1
BmIa/BzLTty39by+dSCmv3/DLdBh9+QLBTg0iVpNjZziBkVaHKdMUGma3UZaoYQK
i1ZkW1bRjPIOrRglrQsbdKQX/yOaAKQisdrElou7bMkdbRdyDh1Tx2pWcZ/33RIN
iAtAY5HKKooDZMRxIQzsoknkMOohvWcAci33sGM1pqrwoYZuhV/VnP/bu5mijmWs
24yOWpshPDUdifgUjMh9WE02ujfIIUsRxcIu1ChzSOzuGYkcWJHQYr8PxYpZWgQX
64bU5OytRxLTdIgExA75sAQwrE9uJODjjyQG9M+BcREIxluFZmu66PybT3iP9W+y
zdLj4aYirYDUijEfVS4lftMbfpVJS7ysW1Elr/C6qyATVmP4p/jLRXzcuB7iCTJR
CsBZiPyC21ECer+J3CftU9Z2gXzDA8hxhu8bGLw2Em+r5nFivl6J2S2dw6A7YKG9
x1i14KF+gqj8o1FLRArXfEIie4GRH6ak57PPgkmvxa222p6Orl7j7t0RBP9XEOj+
/+sVUV/N+DAOncY7/AbWxstyQxMCAwEAAaMbMBkwFwYDVR0RBBAwDoIMc2VydmVy
MS50ZXN0MA0GCSqGSIb3DQEBCwUAA4ICAQAQI+bRplwPgp4mUyS2Iaa0neZtbWuI
+1ol78lGnX6Wy3278Xk4X5iuCZ94oyBPKo5oOPDpONIhLknskszeT12svDy/C9di
KDyYpgYb/IgF8SXkUCuk8NACzhx116GOaKGjHIW0z97bWYP96VRKHpez6Bp4E10i
hJIimh770kltXaWkEEv4Uao4WTc4agkBIPhoA+kdXo+EZSBL5QLGJM0oXcmp3Ifb
94PJNOzv9SdyIyFPA92pOFq+CIa8Kim8J0Zg3aPPmNQWD9+bQuqOlxBTmxwo87pe
h4HOPy4BLBcTVcrQhSDncRkYCze6+CZWzkA9GUO9bhk0JlzWyFIZVu7slkmoOj/I
/C9vhR+qcQr6E+kXLk28nMJ1uX7UspIrPTWUklT96UB8vRy7L27QMdbR7BMW1FNw
FaXZhhDlUA6ElwPYC/S2oPSwDgxUkhGIKE6wifpDBiIYk4FcTp2Eo7lL+wWG5STY
C65JH8qJ0MSdDNAIr4jc4FsAVLxZfSGX9AK2LV9XubfjtQqy3ZDmP0f4OIMJCaR+
8jt8nwmludEDqhdzscp2C/33BMNapgCFGv5/l7UfpMbPPXwHGHMYDG93S1EotbkZ
Zx+Yf54cCWDbgDNTFCTXOQH725oGgrLRfDg5YmS30Ng13nUwAZhEymmGTjlkKWiD
UBAcTvXRU8NjfQ==
-----END CERTIFICATE-----
"""

SERVICES_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAm7Fk6Qi1FOI8mIJlLlqDGTq+l+Ojwhv1q2Vm5/CVw/jUu+5X
nDpw7kRT2huKbSqKB+0aHu0HGSjr0HUcfF6DYOK4uqS8P7VVMqJI/GSgI3FPxIEO
FoP1NW3aEr5y9S+1zhfWOcC4bW1LheB/q3tU2Zl9jHrL3S9MDOmZzvaMIRJx/go5
eQNKspzrOCnYVYj2JggzhgaY1us8Km/Umn371K+6aXOOIsljv27jAgilZ4NqQ4lQ
iRlLrhkcR+VHgLG4REDINF52ZDpJOBPxzihCVGsBTtDCyJfzov9juVl2lAtzRANa
Kxj7VrSQdW5ByJgrnfMMjG2DQWUcHUICic2cmwIDAQABAoIBADltz9kdex3+7Xcb
8hKNFHqD7rW8JDV/drkIKFM5rSSibmX73pkj/XAGCCAVtJPb8xpFXTM3Hz0qmQFF
kYJWooNkXduK1F1zl7+bmOxweZlZPKExMW8gsZxJrvzm/yRtutQQetbGvcCvZgI1
8yHf1kaFlYfx66zku1qv+CodS0cPIVo3ua1Sz8efTxdTTDmm9TPHf5QD/8zGDKKR
manPWIeD6crs4rI+UpBO9n2LAYVmg6wGiLqTR0c47xzi/C7HFaWwzDzsP2DeS1Z1
iURbJVJw2nB/emr/5y9KAL7ARc0cD3JCoR9YinfNj5nmO0WBdi9zOzMG1mLFOpOG
tMVKhpECgYEAzqYzv/OYc1z9xHX+JmrK69LVe7rajo2dBlBbciL1Y5wd1j7jksY0
igo5uUoYarD9AdPC8tJfuPQHQ7HA9cDrZNj4xo1O1EZjzTOGAgNt7GLSfuDFSOSx
5AnTP+CYeXpP31Nmpuyr+NnWwiLg6TrOMXRU7IEw97waa1wpDC4I40UCgYEAwN/o
DhYR8Bw2hAcLD8v/eg/L8HRnJ6eOn9Q12KKaQUTUCwWz0nOX1AZlECubRBdhOeC0
CZ5IicieM22v/RiW24Mak5r7w3ET7L/xof/tVwypYWVyW5kcBmo0SzusgIGkZr0k
+jexuAmFYv0zC0r1gUI8GShhJl7FEvple1M9jl8CgYANtCPWZNcFP3Nspc52ybov
LUoO7HM15No24vlNdlgDhQTNglohD5fIV6lASlOYL6h3iI1zANRsNXKN4KnFIkf5
5hGJSTGjDg/sObB3TbbqaBtBYrJyhQfu8V/a6o/x7lSBoMw74ZH97KQ7N4jmromh
6e7/yAlxRD4URIZMUnkwaQKBgQCeJzvWSRyeYdQGAOx+II21njxhSGHJr2iRAGbC
49pPCMxC2YMxX12xGylF0Cv58p3j4rBebq8WZC3tB9VWWRJinydsv5oQEan/6QiP
CRep2JUPaysRlwPW8sE8q4rwuN2A7Tnj/0U4Hn6ExBBWAzo6qoAzNNwspWs9+5q5
PHFuSwKBgQC7Ar2101GZKkTK3ub8XrSJnJFhqDp7f/0Z+D7Na9n3soREp6uFkORW
1gxV23DL1QH9PqBjhCSIHoIDS18diNNLpsB4W4H/tcLff+ec2hIVomzajC39U3PU
7u4/fIV2eC9tbcxs9ZBJBX8w+IyBZh+xHcvjcc06NO99hUIFdFXRWA==
-----END RSA PRIVATE KEY-----
"""

SERVICES_CERT = """
-----BEGIN CERTIFICATE-----
MIIEAzCCAeugAwIBAgICEAowDQYJKoZIhvcNAQELBQAwNzELMAkGA1UEBhMCR0Ix
CjAIBgNVBAgMASAxCjAIBgNVBAoMASAxEDAOBgNVBAMMB1Rlc3QgQ0EwHhcNMjIx
MTMwMDkwNTM1WhcNMjMxMTMwMDkwNTM1WjA0MQswCQYDVQQGEwJHQjENMAsGA1UE
CgwEdGVzdDEWMBQGA1UEAwwNc2VydmljZXMudGVzdDCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBAJuxZOkItRTiPJiCZS5agxk6vpfjo8Ib9atlZufwlcP4
1LvuV5w6cO5EU9obim0qigftGh7tBxko69B1HHxeg2DiuLqkvD+1VTKiSPxkoCNx
T8SBDhaD9TVt2hK+cvUvtc4X1jnAuG1tS4Xgf6t7VNmZfYx6y90vTAzpmc72jCES
cf4KOXkDSrKc6zgp2FWI9iYIM4YGmNbrPCpv1Jp9+9SvumlzjiLJY79u4wIIpWeD
akOJUIkZS64ZHEflR4CxuERAyDRedmQ6STgT8c4oQlRrAU7QwsiX86L/Y7lZdpQL
c0QDWisY+1a0kHVuQciYK53zDIxtg0FlHB1CAonNnJsCAwEAAaMcMBowGAYDVR0R
BBEwD4INc2VydmljZXMudGVzdDANBgkqhkiG9w0BAQsFAAOCAgEAvjmdvAX4jqn9
ErEekXjMVM//YSZLQVLG70cQNQJDW/4FTcLLKngX0mUDUni0jKISm5WVWKrAqPd1
ctSdiRiDGSSSX5zgNRhJpxy1YlUZhw4iYMuy1zq3LwAW+x220eKGVdqBCVcsjBdg
ZDpYbcDcv5OHjwq4A0V1xfVmhIhYdZaSC8bmoVZRnjLBazqK+B33uRxbof3II8zU
QJEX7c8pPRt32d9kDoygXmT8+AV7TvJ6E+dqxmMJih64Ps7L8vsww5hwEnRhoCla
lWCv4NVkgyitHHxaNZjmQZsNlvOEfveqT4MKD1Tq2MHs4buInRijRTIG2mXzu0in
oCILqp2EktEh+n/jWt2Gk6HHuW7sC2e+RdCjuhckEeA48qCEDyS6NbE7U5s7pGH0
AspL8UuhS8SA5II7xgm63Uta1COAxaP55neeOgVO8xdbznDadze57avVvEN+/lat
VUvKDnBSP7NT83hzqbtuhvFufdnS4XGtnfnF9rGUIN/hpxinoQ2fFRrl7z5kcITP
iV9Rtqis1qh7yEm629KTTeuMvntMlEb0D5DMao++/a/WJR/qBNGVCR7f6Lfia69j
tfJMEhAGbaHdocjY8RxaPdm3GjyvVe742k85HlxjLKVqqqxzeHJmEjsYRf+9Lyl3
+LrenWlNMplFhb+mLdHx3fWPWvLI3eQ=
-----END CERTIFICATE-----
"""

NETWORK_CONFIG = """
{
    "fanout": 1,
    "ca_file": "configs/ca_cert.pem",

    "peers": [
        { "name": "My.Little.Services", "address": "%(services_hostname)s:%(services_port)s", "fingerprint": "95806a3b9b14d0bf47521368d9d1f13a5df89cde" },
        { "name": "My.Little.Server", "address": "%(server1_hostname)s:%(server1_port)s", "fingerprint": "961090b178e037be12a77c0a83876740e3222abd" }
    ]
}
"""

NETWORK_CONFIG_CONFIG = """
{
    "opers": [
        {
            "name": "operuser",
            // echo -n "operpassword" | openssl passwd -6 -stdin
            "hash": "$6$z5yA.OfGliDoi/R2$BgSsguS6bxAsPSCygDisgDw5JZuo5.88eU3Hyc7/4OaNpeKIxWGjOggeHzOl0xLiZg1vfwxXjOTFN14wG5vNI."
        }
    ],

    "alias_users": [
        {
            "nick": "ChanServ",
            "user": "ChanServ",
            "host": "services.",
            "realname": "Channel services compatibility layer",
            "command_alias": "CS"
        },
        {
            "nick": "NickServ",
            "user": "NickServ",
            "host": "services.",
            "realname": "Account services compatibility layer",
            "command_alias": "NS"
        }
    ],

    "default_roles": {
        "builtin:op": [
            "always_send",
            "op_self", "op_grant", "voice_self", "voice_grant",
            "receive_op", "receive_voice", "receive_opmod",
            "topic", "kick", "set_simple_mode", "set_key",
            "ban_view", "ban_add", "ban_remove_any",
            "quiet_view", "quiet_add", "quiet_remove_any",
            "exempt_view", "exempt_add", "exempt_remove_any",
            //"inviteonly_invite_self", "inviteonly_invite_other",
            "invite_self", "invite_other",
            "invex_view", "invex_add", "invex_remove_any"
        ],
        "builtin:voice": [
            "always_send",
            "voice_self",
            "receive_voice",
            "ban_view", "quiet_view"
        ],
        "builtin:all": [
            "ban_view", "quiet_view"
        ]
    },

    "debug_mode": true
}
"""

SERVER_CONFIG = """
{
    "server_id": 1,
    "server_name": "My.Little.Server",

    "management": {
        "address": "%(server1_management_hostname)s:%(server1_management_port)s",
        "client_ca": "configs/ca_cert.pem",
        "authorised_fingerprints": [
            { "name": "user1", "fingerprint": "435bc6db9f22e84ba5d9652432154617c9509370" },
        ],
    },

    "server": {
        "listeners": [
            { "address": "%(c2s_hostname)s:%(c2s_port)s" },
        ],
    },

    "tls_config": {
        "key_file": "configs/server1.key",
        "cert_file": "configs/server1.pem",
    },

    "node_config": {
        "listen_addr": "%(server1_hostname)s:%(server1_port)s",
        "cert_file": "configs/server1.pem",
        "key_file": "configs/server1.key",
    },

    "log": {
        "dir": "log/server1/",

        "module-levels": {
            "": "trace",
        },

        "targets": [
            {
                "target": "stdout",
                "level": "trace",
                "modules": [ "sable", "audit", "client_listener" ],
            },
            /*
            {
                "target": { "filename": "client_listener.log" },
                "level": "trace",
                "modules": [ "client_listener" ],
            },
            */
        ],
    },
}
"""

SERVICES_CONFIG = """
{
    "server_id": 99,
    "server_name": "My.Little.Services",

    "management": {
        "address": "%(services_management_hostname)s:%(services_management_port)s",
        "client_ca": "configs/ca_cert.pem",
        "authorised_fingerprints": [
            { "name": "user1", "fingerprint": "435bc6db9f22e84ba5d9652432154617c9509370" }
        ]
    },

    "server": {
        "database": "test_database.json",
        "default_roles": {
            "builtin:founder": [
                "founder", "access_view", "access_edit", "role_view", "role_edit",
                "op_self", "op_grant",
                "voice_self", "voice_grant",
                "always_send",
                "invite_self", "invite_other",
                "receive_op", "receive_voice", "receive_opmod",
                "topic", "kick", "set_simple_mode", "set_key",
                "ban_view", "ban_add", "ban_remove_any",
                "quiet_view", "quiet_add", "quiet_remove_any",
                "exempt_view", "exempt_add", "exempt_remove_any",
                "invex_view", "invex_add", "invex_remove_any"
            ],
            "builtin:op": [
                "always_send",
                "receive_op", "receive_voice", "receive_opmod",
                "topic", "kick", "set_simple_mode", "set_key",
                "ban_view", "ban_add", "ban_remove_any",
                "quiet_view", "quiet_add", "quiet_remove_any",
                "exempt_view", "exempt_add", "exempt_remove_any",
                "invex_view", "invex_add", "invex_remove_any"
            ],
            "builtin:voice": [
                "always_send", "voice_self", "receive_voice"
            ]
        }
    },

    "tls_config": {
        "key_file": "configs/services.key",
        "cert_file": "configs/services.pem"
    },

    "node_config": {
        "listen_addr": "%(services_hostname)s:%(services_port)s",
        "cert_file": "configs/services.pem",
        "key_file": "configs/services.key"
    },

    "log": {
        "dir": "log/services/",

        "module-levels": {
            "": "trace"
        },

        "targets": [
            {
                "target": "stdout",
                "level": "trace",
                "modules": [ "sable_services" ]
            }
        ]
    }
}
"""


class SableController(BaseServerController, DirectoryBasedController):
    software_name = "Sable"
    supported_sasl_mechanisms = {"PLAIN"}
    sync_sleep_time = 0.1
    """Sable processes commands very quickly, but responses for commands changing the
    state may be sent after later commands for messages which don't."""

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        run_services: bool,
        faketime: Optional[str],
    ) -> None:
        if password is not None:
            raise NotImplementedByController("PASS command")
        if ssl:
            raise NotImplementedByController("SSL")
        assert self.proc is None
        self.port = port
        self.create_config()

        assert self.directory

        (self.directory / "configs").mkdir()

        c2s_hostname = hostname
        c2s_port = port
        del hostname, port

        (server1_hostname, server1_port) = self.get_hostname_and_port()
        (services_hostname, services_port) = self.get_hostname_and_port()
        (server1_management_hostname, server1_management_port) = self.get_hostname_and_port()
        (services_management_hostname, services_management_port) = self.get_hostname_and_port()

        self.template_vars = dict(
            c2s_hostname=c2s_hostname,
            c2s_port=c2s_port,
            server1_hostname=server1_hostname,
            server1_port=server1_port,
            server1_management_hostname=server1_management_hostname,
            server1_management_port=server1_management_port,
            services_hostname=services_hostname,
            services_port=services_port,
            services_management_hostname=services_management_hostname,
            services_management_port=services_management_port,
        )

        with self.open_file("configs/ca_cert.pem") as fd:
            fd.write(CA_CERT)
        with self.open_file("configs/network.conf") as fd:
            fd.write(NETWORK_CONFIG % self.template_vars)
        with self.open_file("configs/network_config.conf") as fd:
            fd.write(NETWORK_CONFIG_CONFIG % self.template_vars)
        with self.open_file("configs/server1.conf") as fd:
            fd.write(SERVER_CONFIG % self.template_vars)
        with self.open_file("configs/server1.key") as fd:
            fd.write(SERVER_KEY)
        with self.open_file("configs/server1.pem") as fd:
            fd.write(SERVER_CERT)

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = subprocess.Popen(
            [
                *faketime_cmd,
                "sable_ircd",
                "--foreground",
                "--server-conf",
                self.directory / "configs/server1.conf",
                "--network-conf",
                self.directory / "configs/network.conf",
                "--bootstrap-network",
                self.directory / "configs/network_config.conf",
            ],
            cwd=self.directory,
            preexec_fn=os.setsid,
        )
        self.pgroup_id = os.getpgid(self.proc.pid)

        if run_services:
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol="sable",
                server_hostname=services_hostname,
                server_port=services_port,
            )

    def kill_proc(self) -> None:
        os.killpg(self.pgroup_id, signal.SIGKILL)
        super().kill_proc()


class SableServicesController(BaseServicesController):
    server_controller: SableController

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        assert protocol == "sable"
        assert self.server_controller.directory is not None

        with self.server_controller.open_file("configs/services.conf") as fd:
            fd.write(SERVICES_CONFIG % self.server_controller.template_vars)
        with self.open_file("configs/services.key") as fd:
            fd.write(SERVICES_KEY)
        with self.open_file("configs/services.pem") as fd:
            fd.write(SERVICES_CERT)

        self.proc = subprocess.Popen(
            [
                "sable_services",
                "--foreground",
                "--server-conf",
                self.server_controller.directory / "configs/services.conf",
                "--network-conf",
                self.server_controller.directory / "configs/network.conf",
            ],
            cwd=self.directory,
            preexec_fn=os.setsid,
        )


def get_irctest_controller_class() -> Type[SableController]:
    return SableController
