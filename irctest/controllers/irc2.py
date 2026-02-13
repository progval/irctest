import shutil
from typing import Optional, Type

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
O:*:operpassword:operuser:::K:
"""


class Irc2Controller(BaseServerController, DirectoryBasedController):
    software_name = "irc2"
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
        faketime: Optional[str],
        websocket_hostname: Optional[str],
        websocket_port: Optional[int],
    ) -> None:
        if websocket_hostname is not None or websocket_port is not None:
            raise NotImplementedByController("Websocket")
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
        pidfile = self.directory / "ircd.pid"
        with self.open_file("server.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    password_field=password_field,
                    pidfile=pidfile,
                )
            )

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = self.execute(
            [
                *faketime_cmd,
                "ircd",
                "-s",  # no iauth
                "-p",
                "on",
                "-f",
                self.directory / "server.conf",
            ],
        )


def get_irctest_controller_class() -> Type[Irc2Controller]:
    return Irc2Controller
