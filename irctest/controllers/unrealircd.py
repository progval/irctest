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
include "modules.default.conf";

me {{
    name "My.Little.Server";
    info "ExampleNET Server";
    sid "001";
}}
admin {{
    "Bob Smith";
    "bob";
    "email@example.org";
}}
class clients {{
    pingfreq 90;
    maxclients 1000;
    sendq 200k;
    recvq 8000;
}}
class servers {{
    pingfreq 60;
    connfreq 15; /* try to connect every 15 seconds */
    maxclients 10; /* max servers */
    sendq 20M;
}}
allow {{
    mask *;
    class clients;
    maxperip 50;
        {password_field}
}}
listen {{
    ip {hostname};
    port {port};
}}
listen {{
    ip {tls_hostname};
    port {tls_port};
    options {{ tls; }}
        tls-options {{
            certificate "{pem_path}";
            key "{key_path}";
        }};
}}

/* Special SSL/TLS servers-only port for linking */
listen {{
    ip {services_hostname};
    port {services_port};
    options {{ serversonly; }}
}}

link services.example.org {{
    incoming {{
        mask *;
    }}
    password "password";
    class servers;
}}
ulines {{
    services.example.org;
}}

set {{
    sasl-server services.example.org;
    kline-address "example@example.org";
    network-name "ExampleNET";
    default-server "irc.example.org";
    help-channel "#Help";
    cloak-keys {{ "aaaA1"; "bbbB2"; "cccC3"; }}
    options {{
        identd-check;  // Disable it, so it doesn't prefix idents with a tilde
    }}
    anti-flood {{
        // Prevent throttling, especially test_buffering.py which
        // triggers anti-flood with its very long lines
        unknown-users {{
            lag-penalty 1;
            lag-penalty-bytes 10000;
        }}
    }}
    modes-on-join "+H 100:1d";  // Enables CHATHISTORY
}}

tld {{
    mask *;
    motd "{empty_file}";
    botmotd "{empty_file}";
    rules "{empty_file}";
}}
"""


class UnrealircdController(BaseServerController, DirectoryBasedController):
    software_name = "UnrealIRCd"
    supported_sasl_mechanisms = {"PLAIN"}
    supports_sts = False

    extban_mute_char = "q"

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
        (services_hostname, services_port) = find_hostname_and_port()

        password_field = 'password "{}";'.format(password) if password else ""

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
        with self.open_file("unrealircd.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    services_hostname=services_hostname,
                    services_port=services_port,
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
                "unrealircd",
                "-t",
                "-F",  # BOOT_NOFORK
                "-f",
                os.path.join(self.directory, "unrealircd.conf"),
            ],
            # stdout=subprocess.DEVNULL,
        )

        if run_services:
            self.wait_for_port()
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol="unreal4",
                server_hostname=services_hostname,
                server_port=services_port,
            )


def get_irctest_controller_class() -> Type[UnrealircdController]:
    return UnrealircdController
