from pathlib import Path
import shutil
from typing import Optional, Set, Type

from irctest.basecontrollers import BaseServerController, DirectoryBasedController
from irctest.runner import NotImplementedByController

TEMPLATE_CONFIG = """
global {{
    name    My.Little.Server;         # IRC name of the server
    info    "located on earth";     # A short info line
}};

options {{
    network_name    unconfigured;
    allow_split_ops;                # Give ops in empty channels

    services_name   My.Little.Services;

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
    "My.Little.Services";
}};


/* class for services */
class {{
    name        services;
    pingfreq    60;         # Idle check every minute
    maxsendq    5000000;    # 5MB backlog buffer
}};

/* our services */
connect {{
    name        My.Little.Services;
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


def initialize_entropy(directory: Path) -> None:
    # https://github.com/DALnet/bahamut/blob/7fc039d403f66a954225c5dc4ad1fe683aedd794/include/dh.h#L35-L38
    nb_rand_bytes = 512 // 8
    # https://github.com/DALnet/bahamut/blob/7fc039d403f66a954225c5dc4ad1fe683aedd794/src/dh.c#L186
    entropy_file_size = nb_rand_bytes * 4

    # Not actually random; but we don't care.
    entropy = b"\x00" * entropy_file_size

    with (directory / ".ircd.entropy").open("wb") as fd:
        fd.write(entropy)


class BahamutController(BaseServerController, DirectoryBasedController):
    software_name = "Bahamut"
    supported_sasl_mechanisms: Set[str] = set()
    supports_sts = False
    nickserv = "NickServ@My.Little.Services"

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
        (services_hostname, services_port) = self.get_hostname_and_port()

        password_field = "passwd {};".format(password) if password else ""

        self.gen_ssl()

        assert self.directory

        # Bahamut reads some bytes from /dev/urandom on startup, which causes
        # GitHub Actions to sometimes freeze and timeout.
        # This initializes the entropy file so Bahamut does not need to do it itself.
        initialize_entropy(self.directory)

        # they are hardcoded... thankfully Bahamut reads them from the CWD.
        shutil.copy(self.pem_path, self.directory / "ircd.crt")
        shutil.copy(self.key_path, self.directory / "ircd.key")

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

        self.proc = self.execute(
            [
                *faketime_cmd,
                "ircd",
                "-t",  # don't fork
                "-f",
                self.directory / "server.conf",
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
