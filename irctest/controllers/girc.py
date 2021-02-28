import subprocess
from typing import Optional, Type

from irctest import authentication, tls
from irctest.basecontrollers import (
    BaseClientController,
    DirectoryBasedController,
    NotImplementedByController,
)


class GircController(BaseClientController, DirectoryBasedController):
    software_name = "gIRC"
    supported_sasl_mechanisms = {"PLAIN"}

    def run(
        self,
        hostname: str,
        port: int,
        auth: Optional[authentication.Authentication],
        tls_config: Optional[tls.TlsConfig] = None,
    ) -> None:
        if tls_config:
            print(tls_config)
            raise NotImplementedByController("TLS options")
        args = ["--host", hostname, "--port", str(port), "--quiet"]

        if auth and auth.username and auth.password:
            args += ["--sasl-name", auth.username]
            args += ["--sasl-pass", auth.password]
            args += ["--sasl-fail-is-ok"]

        # Runs a client with the config given as arguments
        self.proc = subprocess.Popen(["girc_test", "connect"] + args)


def get_irctest_controller_class() -> Type[GircController]:
    return GircController
