import os
import shutil
import subprocess
from typing import Optional, Set, Type

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.irc_utils.junkdrawer import find_hostname_and_port

TEMPLATE_CONFIG = """
global {{
    name    My.Little.Server;         # IRC name of the server
    info    "located on earth";     # A short info line
}};

options {{
    network_name    unconfigured;
    allow_split_ops;                # Give ops in empty channels

    services_name   services.example.org;

    // if you need to link more than 1 server, uncomment the following line
    servtype        hub;
}};

/* where to listen for connections */
port {{
    port    {port};
    bind    {hostname};
}};

/* allow clients to connect */
allow {{
    host    *@*;    # Allow anyone
    class   users;  # Place them in the users class
    flags   T;      # No throttling
    {password_field}
}};

/* connection class for users */
class {{
    name        users;      # Class name
    maxusers    100;        # Maximum connections
    pingfreq    1000;       # Check idle connections every N seconds
    maxsendq    100000;     # 100KB send buffer limit
}};

/* for services */
super {{
    "services.example.org";
}};


/* class for services */
class {{
    name        services;
    pingfreq    60;         # Idle check every minute
    maxsendq    5000000;    # 5MB backlog buffer
}};

/* our services */
connect {{
    name        services.example.org;
    host        *@127.0.0.1;  # unfortunately, masks aren't allowed here
    apasswd     password;
    cpasswd     password;
    class       services;
}};

oper {{
    name operuser;
    host *@*;
    passwd operpassword;
    access  *Aa;
    class users;
}};
"""


class BahamutController(BaseServerController, DirectoryBasedController):
    software_name = "Bahamut"
    supported_sasl_mechanisms: Set[str] = set()
    supports_sts = False
    nickserv = "NickServ@services.example.org"

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
        (unused_hostname, unused_port) = find_hostname_and_port()
        (services_hostname, services_port) = find_hostname_and_port()

        password_field = "passwd {};".format(password) if password else ""

        self.gen_ssl()

        assert self.directory

        # they are hardcoded... thankfully Bahamut reads them from the CWD.
        shutil.copy(self.pem_path, os.path.join(self.directory, "ircd.crt"))
        shutil.copy(self.key_path, os.path.join(self.directory, "ircd.key"))

        with self.open_file("server.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    services_hostname=services_hostname,
                    services_port=services_port,
                    password_field=password_field,
                    # key_path=self.key_path,
                    # pem_path=self.pem_path,
                )
            )

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = subprocess.Popen(
            [
                *faketime_cmd,
                "ircd",
                "-t",  # don't fork
                "-f",
                os.path.join(self.directory, "server.conf"),
            ],
        )

        if run_services:
            self.wait_for_port()
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol="bahamut",
                server_hostname=hostname,
                server_port=port,
            )


def get_irctest_controller_class() -> Type[BahamutController]:
    return BahamutController
