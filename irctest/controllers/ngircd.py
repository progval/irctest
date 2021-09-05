import os
import subprocess
from typing import Optional, Set, Type

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.irc_utils.junkdrawer import find_hostname_and_port

TEMPLATE_CONFIG = """
[Global]
    Name = My.Little.Server
    Info = ExampleNET Server
    Bind = {hostname}
    Ports = {port}
    AdminInfo1 = Bob Smith
    AdminEMail = email@example.org
    {password_field}

[Server]
    Name = services.example.org
    MyPassword = password
    PeerPassword = password
    Passive = yes  # don't connect to it
    ServiceMask = *Serv

[Operator]
    Name = operuser
    Password = operpassword
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
        valid_metadata_keys: Optional[Set[str]] = None,
        invalid_metadata_keys: Optional[Set[str]] = None,
        restricted_metadata_keys: Optional[Set[str]] = None,
    ) -> None:
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                "Defining valid and invalid METADATA keys."
            )
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()
        (unused_hostname, unused_port) = find_hostname_and_port()

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
                    empty_file=os.path.join(self.directory, "empty.txt"),
                )
            )
        self.proc = subprocess.Popen(
            [
                "ngircd",
                "--nodaemon",
                "--config",
                os.path.join(self.directory, "server.conf"),
            ],
            # stdout=subprocess.DEVNULL,
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
