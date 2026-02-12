import shutil
from typing import Optional, Type

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)

TEMPLATE_CONFIG = """
General {{
    name = "My.Little.Server";
    numeric = 42;
    description = "test server";
}};

Port {{
    vhost = "{hostname}";
    port = {port};
}};

Class {{
    name = "Client";
    pingfreq = 5 minutes;
    sendq = 160000;
    maxlinks = 1024;
}};

Client {{
    username = "*";
    class = "Client";
    {password_field}
}};

Operator {{
    local = no;
    host = "*@*";
    password = "$PLAIN$operpassword";
    name = "operuser";
    class = "Client";
}};

features {{
    "PPATH" = "{pidfile}";

    # workaround for whois tests, checking the server name
    "HIS_SERVERNAME" = "My.Little.Server";
}};
"""


class Ircu2Controller(BaseServerController, DirectoryBasedController):
    software_name = "ircu2"
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
        password_field = 'password = "{}";'.format(password) if password else ""
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
                "-n",  # don't detach
                "-f",
                self.directory / "server.conf",
                "-x",
                "DEBUG",
            ],
        )


def get_irctest_controller_class() -> Type[Ircu2Controller]:
    return Ircu2Controller
