import os
import subprocess
from typing import Optional

import irctest
from irctest.basecontrollers import BaseServicesController, DirectoryBasedController
import irctest.cases
import irctest.runner

TEMPLATE_CONFIG = """
loadmodule "modules/protocol/{protocol}";
loadmodule "modules/backend/opensex";
loadmodule "modules/crypto/pbkdf2";

loadmodule "modules/nickserv/main";
loadmodule "modules/nickserv/cert";
loadmodule "modules/nickserv/register";
loadmodule "modules/nickserv/verify";

loadmodule "modules/saslserv/authcookie";
#loadmodule "modules/saslserv/ecdh-x25519-challenge";
loadmodule "modules/saslserv/ecdsa-nist256p-challenge";
loadmodule "modules/saslserv/external";
loadmodule "modules/saslserv/plain";
#loadmodule "modules/saslserv/scram";

serverinfo {{
    name = "services.example.org";
    desc = "Atheme IRC Services";
    numeric = "00A";
    netname = "testnet";
    adminname = "no admin";
    adminemail = "no-admin@example.org";
    registeremail = "registration@example.org";
    auth = none;  // Disable email check
}};

general {{
    commit_interval = 5;
}};

uplink "My.Little.Server" {{
    host = "{server_hostname}";
    port = {server_port};
    send_password = "password";
    receive_password = "password";
}};

saslserv {{
    nick = "SaslServ";
}};
"""


class AthemeServices(BaseServicesController, DirectoryBasedController):
    """Mixin for server controllers that rely on Atheme"""

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        self.create_config()

        assert protocol in ("inspircd", "charybdis", "unreal4")

        with self.open_file("services.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    protocol=protocol,
                    server_hostname=server_hostname,
                    server_port=server_port,
                )
            )

        assert self.directory
        self.proc = subprocess.Popen(
            [
                "atheme-services",
                "-n",  # don't fork
                "-c",
                os.path.join(self.directory, "services.conf"),
                "-l",
                f"/tmp/services-{server_port}.log",
                "-p",
                os.path.join(self.directory, "services.pid"),
                "-D",
                self.directory,
            ],
            stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        assert password
        if len(password.encode()) > 288:
            # It's hardcoded at compile-time :(
            # https://github.com/atheme/atheme/blob/4fa0e03bd3ce2cb6041a339f308616580c5aac29/include/atheme/constants.h#L51
            raise irctest.runner.NotImplementedByController("Passwords over 288 bytes")

        super().registerUser(case, username, password)
