import functools
from pathlib import Path
import shutil
import subprocess
from typing import Tuple, Type

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
    maxpasslen = 1000
    minpasslen = 1
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

module {{ name = "{module_prefix}sasl" }}
module {{ name = "enc_sha256" }}
module {{ name = "ns_cert" }}

"""


@functools.lru_cache()
def installed_version() -> Tuple[int, ...]:
    output = subprocess.run(
        ["anope", "--version"], stdout=subprocess.PIPE, universal_newlines=True
    ).stdout
    (anope, version, *trailing) = output.split()[0].split("-")
    assert anope == "Anope"
    return tuple(map(int, version.split(".")))


class AnopeController(BaseServicesController, DirectoryBasedController):
    """Collaborator for server controllers that rely on Anope"""

    software_name = "Anope"
    software_version = None

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

        assert self.directory
        services_path = shutil.which("anope")
        assert services_path

        # Rewrite Anope 2.0 module names for 2.1
        if not self.software_version:
            self.software_version = installed_version()
        if self.software_version >= (2, 1, 0):
            if protocol == "charybdis":
                protocol = "solanum"
            elif protocol == "inspircd3":
                protocol = "inspircd"
            elif protocol == "unreal4":
                protocol = "unrealircd"

        with self.open_file("conf/services.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    protocol=protocol,
                    server_hostname=server_hostname,
                    server_port=server_port,
                    module_prefix="" if self.software_version >= (2, 1, 2) else "m_",
                )
            )

        with self.open_file("conf/empty_file") as fd:
            pass

        # Config and code need to be in the same directory, *obviously*
        (self.directory / "lib").symlink_to(Path(services_path).parent.parent / "lib")

        self.proc = subprocess.Popen(
            [
                "anope",
                "--config=services.conf",  # can't be an absolute path in 2.0
                "--nofork",  # don't fork
                "--nopid",  # don't write a pid
            ],
            cwd=self.directory,
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )


def get_irctest_controller_class() -> Type[AnopeController]:
    return AnopeController
