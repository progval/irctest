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
serverinfo {{
    name = "My.Little.Server";
    sid = "42X";
    description = "test server";
{ssl_config}
}};

general {{
    throttle_count = 100;  # We need to connect lots of clients quickly
    sasl_service = "SaslServ";
}};

class "server" {{
    ping_time = 5 minutes;
    connectfreq = 5 minutes;
}};

listen {{
    defer_accept = yes;

    host = "{hostname}";
    port = {port};
}};

auth {{
    user = "*";
    flags = exceed_limit;
    {password_field}
}};

channel {{
    disable_local_channels = no;
    no_create_on_split = no;
    no_join_on_split = no;
    displayed_usercount = 0;
}};

connect "services.example.org" {{
    host = "localhost";  # Used to validate incoming connection
    port = 0;  # We don't want the servers to connect to services
    send_password = "password";
    accept_password = "password";
    class = "server";
    flags = topicburst;
}};
service {{
    name = "services.example.org";
}};
"""

TEMPLATE_SSL_CONFIG = """
    ssl_private_key = "{key_path}";
    ssl_cert = "{pem_path}";
    ssl_dh_params = "{dh_path}";
"""


class CharybdisController(BaseServerController, DirectoryBasedController):
    software_name = "Charybdis"
    binary_name = "charybdis"
    supported_sasl_mechanisms = {"PLAIN"}
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
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    services_hostname=services_hostname,
                    services_port=services_port,
                    password_field=password_field,
                    ssl_config=ssl_config,
                )
            )
        assert self.directory
        self.proc = subprocess.Popen(
            [
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
                protocol="charybdis", server_hostname=hostname, server_port=port
            )


def get_irctest_controller_class() -> Type[CharybdisController]:
    return CharybdisController
