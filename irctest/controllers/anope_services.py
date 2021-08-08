import os
import shutil
import subprocess
from typing import Type

from irctest.basecontrollers import BaseServicesController, DirectoryBasedController

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
}}

mail {{
    usemail = no
}}

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

        assert protocol in ("inspircd3", "charybdis", "hybrid", "plexus", "unreal4")

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


def get_irctest_controller_class() -> Type[AnopeController]:
    return AnopeController
