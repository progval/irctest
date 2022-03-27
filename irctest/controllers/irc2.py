import os
import subprocess
from typing import Optional, Set, Type

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)

TEMPLATE_CONFIG = """
# M:<Server NAME>:<YOUR Internet IP#>:<Geographic Location>:<Port>:<SID>:
M:My.Little.Server:{hostname}:test server:{port}:0042:

# A:<Your Name/Location>:<Your E-Mail Addr>:<other info>::<network name>:
A:Organization, IRC dept.:Daemon <ircd@example.irc.org>:Client Server::IRCnet:

# P:<YOUR Internet IP#>:<*>::<Port>:<Flags>
P::::{port}::

# Y:<Class>:<Ping Frequency>::<Max Links>:<SendQ>:<Local Limit>:<Global Limit>:
Y:10:90::100:512000:100.100:100.100:

# I:<TARGET Host Addr>:<Password>:<TARGET Hosts NAME>:<Port>:<Class>:<Flags>:
I::{password_field}:::10::

# O:<TARGET Host NAME>:<Password>:<Nickname>:<Port>:<Class>:<Flags>:
O:*:operpassword:operuser::::
"""


class Ircu2Controller(BaseServerController, DirectoryBasedController):
    binary_name: str
    services_protocol: str

    supports_sts = False
    extban_mute_char = None

    def create_config(self) -> None:
        super().create_config()
        with self.open_file("server.conf"):
            pass

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        run_services: bool,
        valid_metadata_keys: Optional[Set[str]] = None,
        invalid_metadata_keys: Optional[Set[str]] = None,
    ) -> None:
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                "Defining valid and invalid METADATA keys."
            )
        if ssl:
            raise NotImplementedByController("TLS")
        if run_services:
            raise NotImplementedByController("Services")
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()
        password_field = password if password else ""
        assert self.directory
        pidfile = os.path.join(self.directory, "ircd.pid")
        with self.open_file("server.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    password_field=password_field,
                    pidfile=pidfile,
                )
            )
        self.proc = subprocess.Popen(
            [
                "ircd",
                "-s",  # no iauth
                "-p",
                "on",
                "-f",
                os.path.join(self.directory, "server.conf"),
            ],
            # stderr=subprocess.DEVNULL,
        )


def get_irctest_controller_class() -> Type[Ircu2Controller]:
    return Ircu2Controller
