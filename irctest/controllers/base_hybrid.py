import os
import shutil
import subprocess
from typing import Optional, Set

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.irc_utils.junkdrawer import find_hostname_and_port

TEMPLATE_SSL_CONFIG = """
    ssl_private_key = "{key_path}";
    ssl_cert = "{pem_path}";
    ssl_dh_params = "{dh_path}";
"""


class BaseHybridController(BaseServerController, DirectoryBasedController):
    """A base class for all controllers derived from ircd-hybrid (Hybrid itself,
    Charybdis, Solanum, ...)"""

    binary_name: str
    services_protocol: str

    supports_sts = False
    extban_mute_char = None

    template_config: str

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
        faketime: Optional[str],
    ) -> None:
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                "Defining valid and invalid METADATA keys."
            )
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()
        (services_hostname, services_port) = find_hostname_and_port()
        password_field = 'password = "{}";'.format(password) if password else ""
        if ssl:
            self.gen_ssl()
            ssl_config = TEMPLATE_SSL_CONFIG.format(
                key_path=self.key_path, pem_path=self.pem_path, dh_path=self.dh_path
            )
        else:
            ssl_config = ""
        with self.open_file("server.conf") as fd:
            fd.write(
                (self.template_config).format(
                    hostname=hostname,
                    port=port,
                    services_hostname=services_hostname,
                    services_port=services_port,
                    password_field=password_field,
                    ssl_config=ssl_config,
                )
            )
        assert self.directory

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = subprocess.Popen(
            [
                *faketime_cmd,
                self.binary_name,
                "-foreground",
                "-configfile",
                os.path.join(self.directory, "server.conf"),
                "-pidfile",
                os.path.join(self.directory, "server.pid"),
            ],
            # stderr=subprocess.DEVNULL,
        )

        if run_services:
            self.wait_for_port()
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol=self.services_protocol,
                server_hostname=hostname,
                server_port=services_port,
            )
