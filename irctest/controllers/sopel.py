from pathlib import Path
import tempfile
from typing import Optional, TextIO, Type, cast

from irctest import authentication, tls
from irctest.basecontrollers import (
    BaseClientController,
    NotImplementedByController,
    TestCaseControllerConfig,
)

TEMPLATE_CONFIG = """
[core]
nick = Sopel
host = {hostname}
use_ssl = false
port = {port}
owner = me
channels =
timeout = 5
auth_username = {username}
auth_password = {password}
{auth_method}
"""


class SopelController(BaseClientController):
    software_name = "Sopel"
    supported_sasl_mechanisms = {"PLAIN"}
    supports_sts = False

    def __init__(self, test_config: TestCaseControllerConfig):
        super().__init__(test_config)
        self.filename = next(tempfile._get_candidate_names()) + ".cfg"  # type: ignore

    def kill(self) -> None:
        super().kill()
        if self.filename:
            try:
                (Path("~/.sopel/").expanduser() / self.filename).unlink()
            except OSError:  # File does not exist
                pass

    def open_file(self, filename: str, mode: str = "a") -> TextIO:
        dir_path = Path("~/.sopel/").expanduser()
        dir_path.mkdir(parents=True, exist_ok=True)
        return cast(TextIO, (dir_path / filename).open(mode))

    def create_config(self) -> None:
        with self.open_file(self.filename):
            pass

    def run(
        self,
        hostname: str,
        port: int,
        auth: Optional[authentication.Authentication],
        tls_config: Optional[tls.TlsConfig] = None,
    ) -> None:
        # Runs a client with the config given as arguments
        if tls_config is not None:
            raise NotImplementedByController("TLS configuration")
        assert self.proc is None
        self.create_config()
        with self.open_file(self.filename) as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    username=auth.username if auth else "",
                    password=auth.password if auth else "",
                    auth_method="auth_method = sasl" if auth else "",
                )
            )
        self.proc = self.execute(["sopel", "-c", self.filename])


def get_irctest_controller_class() -> Type[SopelController]:
    return SopelController
