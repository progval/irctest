import functools
import re
import subprocess
from typing import Optional, Tuple, Type

import irctest
from irctest.basecontrollers import BaseServicesController, DirectoryBasedController
import irctest.cases
import irctest.runner

TEMPLATE_CONFIG = """
loadmodule "{module_path}protocol/{protocol}";
loadmodule "{module_path}backend/opensex";
loadmodule "{module_path}crypto/pbkdf2v2";
loadmodule "{module_path}crypto/pbkdf2";

loadmodule "{module_path}nickserv/main";
loadmodule "{module_path}nickserv/cert";
loadmodule "{module_path}nickserv/register";
loadmodule "{module_path}nickserv/verify";

loadmodule "{module_path}saslserv/main";
loadmodule "{module_path}saslserv/authcookie";
#loadmodule "{module_path}saslserv/ecdh-x25519-challenge";
loadmodule "{module_path}saslserv/ecdsa-nist256p-challenge";
loadmodule "{module_path}saslserv/external";
loadmodule "{module_path}saslserv/plain";
#loadmodule "{module_path}saslserv/scram";

serverinfo {{
    name = "My.Little.Services";
    desc = "Atheme IRC Services";
    numeric = "00A";
    netname = "testnet";
    adminname = "no admin";
    adminemail = "no-admin@example.org";
    registeremail = "registration@example.org";
    auth = none;  // Disable email check
    casemapping = "{casemapping}";
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


@functools.lru_cache()
def installed_version() -> Tuple[int, ...]:
    output = subprocess.run(
        ["atheme-services", "-v"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ).stdout
    version = re.search(
        r"Atheme IRC Services \((?:atheme )?(\d+)\.(\d+)\.(\d+)", output
    )
    assert version
    return tuple(map(int, version.groups()))


class AthemeController(BaseServicesController, DirectoryBasedController):
    """Mixin for server controllers that rely on Atheme"""

    software_name = "Atheme"
    software_version = None

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        self.create_config()

        if protocol == "inspircd3":
            # That's the name used by Anope
            protocol = "inspircd"
        assert protocol in (
            "bahamut",
            "charybdis",
            "inspircd",
            "ngircd",
            "solanum",
            "unreal4",
        )

        if not self.software_version:
            self.software_version = installed_version()

        # Atheme 7.3+ no longer includes the modules directory in the path.
        module_path = ""
        if self.software_version < (7, 3, 0):
            module_path = "modules/"

        casemapping = "rfc1459"
        if protocol in ("bahamut", "inspircd", "unreal4"):
            casemapping = "ascii"

        with self.open_file("services.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    casemapping=casemapping,
                    module_path=module_path,
                    protocol=protocol,
                    server_hostname=server_hostname,
                    server_port=server_port,
                )
            )

        assert self.directory

        # Atheme 7.3+ requires a database to run.
        with self.open_file("services.db") as fd:
            pass

        self.proc = self.execute(
            [
                "atheme-services",
                "-n",  # don't fork
                "-c",
                self.directory / "services.conf",
                "-l",
                f"/tmp/services-{server_port}.log",
                "-p",
                self.directory / "services.pid",
                "-D",
                self.directory,
            ],
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


def get_irctest_controller_class() -> Type[AthemeController]:
    return AthemeController
