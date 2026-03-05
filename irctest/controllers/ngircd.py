import shutil
from typing import Optional, Set, Type

from irctest.basecontrollers import BaseServerController, DirectoryBasedController
from irctest.runner import NotImplementedByController

TEMPLATE_CONFIG = """
[Global]
    Name = My.Little.Server
    Info = test server
    Bind = {hostname}
    Ports = {port}
    AdminInfo1 = Bob Smith
    AdminEMail = email@example.org
    {password_field}

[Server]
    Name = My.Little.Services
    MyPassword = password
    PeerPassword = password
    Passive = yes  # don't connect to it
    ServiceMask = *Serv

[Options]
    MorePrivacy = no  # by default, always replies to WHOWAS with ERR_WASNOSUCHNICK
    PAM = no

[Operator]
    Name = operuser
    Password = operpassword

[Limits]
    MaxNickLength = 32  # defaults to 9
"""


class NgircdController(BaseServerController, DirectoryBasedController):
    software_name = "ngIRCd"
    supported_sasl_mechanisms: Set[str] = set()
    supports_sts = False

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
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()
        (unused_hostname, unused_port) = self.get_hostname_and_port()

        password_field = "Password = {}".format(password) if password else ""

        self.gen_ssl()
        if ssl:
            (tls_hostname, tls_port) = (hostname, port)
            (hostname, port) = (unused_hostname, unused_port)
        else:
            # Unreal refuses to start without TLS enabled
            (tls_hostname, tls_port) = (unused_hostname, unused_port)

        with self.open_file("empty.txt") as fd:
            fd.write("\n")

        assert self.directory

        with self.open_file("server.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    tls_hostname=tls_hostname,
                    tls_port=tls_port,
                    password_field=password_field,
                    key_path=self.key_path,
                    pem_path=self.pem_path,
                    empty_file=self.directory / "empty.txt",
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
                "ngircd",
                "--nodaemon",
                "--config",
                self.directory / "server.conf",
            ],
        )

        if run_services:
            self.wait_for_port()
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol="ngircd",
                server_hostname=hostname,
                server_port=port,
            )


def get_irctest_controller_class() -> Type[NgircdController]:
    return NgircdController
