import os
import shutil
import subprocess
from typing import Any, Optional, Type

from irctest import cases, runner
from irctest.basecontrollers import BaseServicesController, DirectoryBasedController
from irctest.client_mock import ClientMock
from irctest.irc_utils.sasl import sasl_plain_blob

TEMPLATE_CONFIG = """
serverinfo {{
    name = "services.example.org"
    description = "Anope IRC Services"
    numeric = "00A"
    pid = "services.pid"
    motd = "conf/empty_file"
}}

uplink  {{
    host = "{server_hostname}"
    port = {server_port}
    password = "password"
}}

module {{
    name = "{protocol}"
}}

networkinfo {{
    networkname = "testnet"
    nicklen = 31
    userlen = 10
    hostlen = 64
    chanlen = 32
    vhost_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
}}

mail {{
    usemail = no
}}

/************************
 * NickServ:
 */

service {{
    nick = "NickServ"
    user = "services"
    host = "services.host"
    gecos = "Nickname Registration Service"
}}

module {{
    name = "nickserv"
    client = "NickServ"
    forceemail = no
    passlen = 1000  # Some tests need long passwords
}}
command {{ service = "NickServ"; name = "HELP"; command = "generic/help"; }}

module {{
    name = "ns_register"
    registration = "none"
}}
command {{ service = "NickServ"; name = "REGISTER"; command = "nickserv/register"; }}


/************************
 * HostServ:
 */

service {{
    nick = "HostServ"
    user = "services"
    host = "services.host"
    gecos = "vHost Service"
}}
module {{
    name = "hostserv"
    client = "HostServ"
}}
module {{ name = "hs_set" }}
command {{ service = "HostServ"; name = "SET"; command = "hostserv/set"; }}


/************************
 * Misc:
 */

options {{
    casemap = "ascii"
    readtimeout = 5s
    warningtimeout = 4h
}}

module {{ name = "m_sasl" }}
module {{ name = "enc_sha256" }}
module {{ name = "ns_cert" }}
"""


class AnopeController(BaseServicesController, DirectoryBasedController):
    """Collaborator for server controllers that rely on Anope"""

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        self.create_config()

        assert protocol in (
            "bahamut",
            "inspircd3",
            "charybdis",
            "hybrid",
            "plexus",
            "unreal4",
            "ngircd",
        )

        with self.open_file("conf/services.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    protocol=protocol,
                    server_hostname=server_hostname,
                    server_port=server_port,
                )
            )

        with self.open_file("conf/empty_file") as fd:
            pass

        assert self.directory

        # Config and code need to be in the same directory, *obviously*
        os.symlink(
            os.path.join(
                os.path.dirname(shutil.which("services")), "..", "lib"  # type: ignore
            ),
            os.path.join(self.directory, "lib"),
        )

        self.proc = subprocess.Popen(
            [
                "services",
                "-n",  # don't fork
                "--config=services.conf",  # can't be an absolute path
                # "--logdir",
                # f"/tmp/services-{server_port}.log",
            ],
            cwd=self.directory,
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )

    def registerUser(
        self,
        case: cases.BaseServerTestCase,  # type: ignore
        username: str,
        password: Optional[str] = None,
        vhost: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().registerUser(case, username, password)

        if vhost:
            if not password:
                raise runner.NotImplementedByController(
                    "vHost for users with no password"
                )
            c = ClientMock(name="setVhost", show_io=True)
            c.connect(self.server_controller.hostname, self.server_controller.port)
            c.sendLine("CAP REQ :sasl")
            c.sendLine("NICK " + username)
            c.sendLine("USER r e g :user")
            while c.getMessage(synchronize=False).command != "CAP":
                pass
            c.sendLine("AUTHENTICATE PLAIN")
            while c.getMessage(synchronize=False).command != "AUTHENTICATE":
                pass
            c.sendLine(sasl_plain_blob(username, password))
            c.sendLine("CAP END")
            while c.getMessage(synchronize=False).command != "001":
                pass
            c.getMessages()
            c.sendLine(f"PRIVMSG HostServ :SET {username} {vhost}")
            self.getServiceResponse(c)


def get_irctest_controller_class() -> Type[AnopeController]:
    return AnopeController
