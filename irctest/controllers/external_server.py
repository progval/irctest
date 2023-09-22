import os
from typing import Optional, Tuple, Type

from irctest.basecontrollers import BaseServerController


class ExternalServerController(BaseServerController):
    """Dummy controller that doesn't run a server.
    Instead, it allows connecting to servers ran outside irctest."""

    software_name = "unknown external server"
    supported_sasl_mechanisms = set(
        os.environ.get("IRCTEST_SERVER_SASL_MECHS", "").split()
    )

    def check_is_alive(self) -> None:
        pass

    def kill_proc(self) -> None:
        pass

    def wait_for_port(self) -> None:
        pass

    def get_hostname_and_port(self) -> Tuple[str, int]:
        hostname = os.environ.get("IRCTEST_SERVER_HOSTNAME")
        port = os.environ.get("IRCTEST_SERVER_PORT")
        if not hostname or not port:
            raise RuntimeError(
                "Please set IRCTEST_SERVER_HOSTNAME and IRCTEST_SERVER_PORT."
            )
        return (hostname, int(port))

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        run_services: bool,
        faketime: Optional[str],
    ) -> None:
        pass


def get_irctest_controller_class() -> Type[ExternalServerController]:
    return ExternalServerController
