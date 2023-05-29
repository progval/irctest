import contextlib
import fcntl
import functools
from pathlib import Path
import shutil
import subprocess
import textwrap
from typing import Callable, ContextManager, Iterator, Optional, Type

from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
include "modules.default.conf";
include "operclass.default.conf";
{extras}
include "help/help.conf";

me {{
    name "My.Little.Server";
    info "test server";
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
            nick-flood 255:10;
            lag-penalty 1;
            lag-penalty-bytes 10000;
        }}
    }}
    modes-on-join "+H 100:1d";  // Enables CHATHISTORY

    {set_v6only}

}}

tld {{
    mask *;
    motd "{empty_file}";
    botmotd "{empty_file}";
    rules "{empty_file}";
}}

files {{
    tunefile "{empty_file}";
}}

oper "operuser" {{
    password = "operpassword";
    mask *;
    class clients;
    operclass netadmin;
}}
"""

SET_V6ONLY = """
// Remove RPL_WHOISSPECIAL used to advertise security groups
whois-details {
    security-groups { everyone none; self none; oper none; }
}

plaintext-policy {
    server warn; // https://www.unrealircd.org/docs/FAQ#server-requires-tls
    oper warn; // https://www.unrealircd.org/docs/FAQ#oper-requires-tls
}

anti-flood {
    everyone {
        connect-flood 255:10;
    }
}
"""


def _filelock(path: Path) -> Callable[[], ContextManager]:
    """Alternative to :cls:`multiprocessing.Lock` that works with pytest-xdist"""

    @contextlib.contextmanager
    def f() -> Iterator[None]:
        with open(path, "a") as fd:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield

    return f


_UNREALIRCD_BIN = shutil.which("unrealircd")
if _UNREALIRCD_BIN:
    _UNREALIRCD_PREFIX = Path(_UNREALIRCD_BIN).parent.parent

    # Try to keep that lock file specific to this Unrealircd instance
    _LOCK_PATH = _UNREALIRCD_PREFIX / "irctest-unrealircd-startstop.lock"
else:
    # unrealircd not found; we are probably going to crash later anyway...
    _LOCK_PATH = Path("/tmp/irctest-unrealircd-startstop.lock")

_STARTSTOP_LOCK = _filelock(_LOCK_PATH)
"""
Unreal cleans its tmp/ directory after each run, which prevents
multiple processes from starting/stopping at the same time.
"""


@functools.lru_cache()
def installed_version() -> int:
    output = subprocess.check_output(["unrealircd", "-v"], universal_newlines=True)
    if output.startswith("UnrealIRCd-5."):
        return 5
    elif output.startswith("UnrealIRCd-6."):
        return 6
    else:
        assert False, f"unexpected version: {output}"


class UnrealircdController(BaseServerController, DirectoryBasedController):
    software_name = "UnrealIRCd"
    supported_sasl_mechanisms = {"PLAIN"}
    supports_sts = False

    extban_mute_char = "quiet" if installed_version() >= 6 else "q"
    software_version = installed_version()

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
    ) -> None:
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()

        if installed_version() >= 6:
            extras = textwrap.dedent(
                """
                include "snomasks.default.conf";
                loadmodule "cloak_md5";
                """
            )
            set_v6only = SET_V6ONLY
        else:
            extras = ""
            set_v6only = ""

        with self.open_file("empty.txt") as fd:
            fd.write("\n")

        password_field = 'password "{}";'.format(password) if password else ""

        (services_hostname, services_port) = self.get_hostname_and_port()
        (unused_hostname, unused_port) = self.get_hostname_and_port()

        self.gen_ssl()
        if ssl:
            (tls_hostname, tls_port) = (hostname, port)
            (hostname, port) = (unused_hostname, unused_port)
        else:
            # Unreal refuses to start without TLS enabled
            (tls_hostname, tls_port) = (unused_hostname, unused_port)

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
                    empty_file=self.directory / "empty.txt",
                    set_v6only=set_v6only,
                    extras=extras,
                )
            )

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        with _STARTSTOP_LOCK():
            self.proc = subprocess.Popen(
                [
                    *faketime_cmd,
                    "unrealircd",
                    "-t",
                    "-F",  # BOOT_NOFORK
                    "-f",
                    self.directory / "unrealircd.conf",
                ],
                # stdout=subprocess.DEVNULL,
            )
            self.wait_for_port()

        if run_services:
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol="unreal4",
                server_hostname=services_hostname,
                server_port=services_port,
            )

    def kill_proc(self) -> None:
        assert self.proc

        with _STARTSTOP_LOCK():
            self.proc.kill()
            self.proc.wait(5)  # wait for it to actually die
            self.proc = None


def get_irctest_controller_class() -> Type[UnrealircdController]:
    return UnrealircdController
