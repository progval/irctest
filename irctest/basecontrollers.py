from __future__ import annotations

import contextlib
import dataclasses
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import textwrap
import time
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
)

import irctest

from . import authentication, tls
from .client_mock import ClientMock
from .irc_utils.filelock import FileLock
from .irc_utils.junkdrawer import find_hostname_and_port
from .irc_utils.message_parser import Message
from .runner import NotImplementedByController


class ProcessStopped(Exception):
    """Raised when the controlled process stopped unexpectedly"""

    pass


@dataclasses.dataclass
class TestCaseControllerConfig:
    """Test-case-specific configuration passed to the controller.
    This is usually used to ask controllers to enable a feature;
    but should not be an issue if controllers enable it all the time."""

    chathistory: bool = False
    """Whether to enable chathistory features."""

    account_registration_before_connect: bool = False
    """Whether draft/account-registration should be allowed before completing
    connection registration (NICK + USER + CAP END)"""

    account_registration_requires_email: bool = False
    """Whether an email address must be provided when using draft/account-registration.
    This does not imply servers must validate it."""

    ergo_roleplay: bool = False
    """Whether to enable the Ergo role-play commands."""

    ergo_config: Optional[Callable[[Dict], Any]] = None
    """Oragono-specific configuration function that alters the dict in-place
    This should be used as little as possible, using the other attributes instead;
    as they are work with any controller."""


class _BaseController:
    """Base class for software controllers.

    A software controller is an object that handles configuring and running
    a process (eg. a server or a client), as well as sending it instructions
    that are not part of the IRC specification."""

    # set by conftest.py
    openssl_bin: str

    supports_sts: bool
    supported_sasl_mechanisms: Set[str]

    proc: Optional[subprocess.Popen]

    _used_ports_path = Path(tempfile.gettempdir()) / "irctest_ports.json"
    _port_lock = FileLock(Path(tempfile.gettempdir()) / "irctest_ports.json.lock")

    def __init__(self, test_config: TestCaseControllerConfig):
        self.debug_mode = os.getenv("IRCTEST_DEBUG_LOGS", "0").lower() in ("true", "1")
        self.test_config = test_config
        self.proc = None
        self._own_ports: Set[Tuple[str, int]] = set()

    @contextlib.contextmanager
    def _used_ports(self) -> Iterator[Set[Tuple[str, int]]]:
        with self._port_lock:
            if not self._used_ports_path.exists():
                self._used_ports_path.write_text("[]")
            used_ports = {
                (h, p) for (h, p) in json.loads(self._used_ports_path.read_text())
            }
            yield used_ports
            self._used_ports_path.write_text(json.dumps(list(used_ports)))

    def get_hostname_and_port(self) -> Tuple[str, int]:
        with self._used_ports() as used_ports:
            while True:
                (hostname, port) = find_hostname_and_port()
                if (hostname, port) not in used_ports:
                    # double-checking in self._used_ports to prevent collisions
                    # between controllers starting at the same time.
                    break

            used_ports.add((hostname, port))
            self._own_ports.add((hostname, port))

        return (hostname, port)

    def check_is_alive(self) -> None:
        assert self.proc
        self.proc.poll()
        if self.proc.returncode is not None:
            raise ProcessStopped(f"process returned {self.proc.returncode}")

    def kill_proc(self) -> None:
        """Terminates the controlled process, waits for it to exit, and
        eventually kills it."""
        assert self.proc
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None

    def kill(self) -> None:
        """Calls `kill_proc` and cleans the configuration."""
        if self.proc:
            self.kill_proc()

        with self._used_ports() as used_ports:
            for hostname, port in list(self._own_ports):
                used_ports.remove((hostname, port))
                self._own_ports.remove((hostname, port))

    def execute(
        self, command: Sequence[Union[str, Path]], **kwargs: Any
    ) -> subprocess.Popen:
        output_to = None if self.debug_mode else subprocess.DEVNULL
        return subprocess.Popen(command, stderr=output_to, stdout=output_to, **kwargs)


class DirectoryBasedController(_BaseController):
    """Helper for controllers whose software configuration is based on an
    arbitrary directory."""

    directory: Optional[Path]

    def __init__(self, test_config: TestCaseControllerConfig):
        super().__init__(test_config)
        self.directory = None

    def kill(self) -> None:
        """Calls `kill_proc` and cleans the configuration."""
        super().kill()
        if self.directory:
            shutil.rmtree(self.directory)

    def terminate(self) -> None:
        """Stops the process gracefully, and does not clean its config."""
        assert self.proc
        self.proc.terminate()
        self.proc.wait()
        self.proc = None

    def open_file(self, name: str, mode: str = "a") -> IO:
        """Open a file in the configuration directory."""
        assert self.directory
        if os.sep in name:
            dir_ = self.directory / os.path.dirname(name)
            dir_.mkdir(parents=True, exist_ok=True)
            assert dir_.is_dir()
        return (self.directory / name).open(mode)

    def create_config(self) -> None:
        if not self.directory:
            self.directory = Path(tempfile.mkdtemp())

    def gen_ssl(self) -> None:
        assert self.directory
        self.csr_path = self.directory / "ssl.csr"
        self.key_path = self.directory / "ssl.key"
        self.pem_path = self.directory / "ssl.pem"
        self.dh_path = self.directory / "dh.pem"
        subprocess.check_output(
            [
                self.openssl_bin,
                "req",
                "-new",
                "-newkey",
                "rsa",
                "-nodes",
                "-out",
                self.csr_path,
                "-keyout",
                self.key_path,
                "-batch",
            ],
            stderr=subprocess.DEVNULL,
        )
        subprocess.check_output(
            [
                self.openssl_bin,
                "x509",
                "-req",
                "-in",
                self.csr_path,
                "-signkey",
                self.key_path,
                "-out",
                self.pem_path,
            ],
            stderr=subprocess.DEVNULL,
        )
        with self.dh_path.open("w") as fd:
            fd.write(
                textwrap.dedent(
                    """
                    -----BEGIN DH PARAMETERS-----
                    MIGHAoGBAJICSyQAiLj1fw8b5xELcnpqBQ+wvOyKgim4IetWOgZnRQFkTgOeoRZD
                    HksACRFJL/EqHxDKcy/2Ghwr2axhNxSJ+UOBmraP3WfodV/fCDPnZ+XnI9fjHsIr
                    rjisPMqomjXeiTB1UeAHvLUmCK4yx6lpAJsCYwJjsqkycUfHiy1bAgEC
                    -----END DH PARAMETERS-----
                    """
                )
            )


class BaseClientController(_BaseController):
    """Base controller for IRC clients."""

    def run(
        self,
        hostname: str,
        port: int,
        auth: Optional[authentication.Authentication],
        tls_config: Optional[tls.TlsConfig] = None,
    ) -> None:
        raise NotImplementedError()


class BaseServerController(_BaseController):
    """Base controller for IRC server."""

    software_name: str  # Class property
    _port_wait_interval = 0.1
    port_open = False
    port: int
    hostname: str
    services_controller: Optional[BaseServicesController] = None
    services_controller_class: Type[BaseServicesController]
    extban_mute_char: Optional[str] = None
    """Character used for the 'mute' extban"""
    nickserv = "NickServ"
    sync_sleep_time = 0.0
    """How many seconds to sleep before clients synchronously get messages.

    This can be 0 for servers answering all commands in order (all but Sable as of
    this writing), as irctest emits a PING, waits for a PONG, and captures all messages
    between the two."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.faketime_enabled = False

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
        raise NotImplementedError()

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,  # type: ignore
        username: str,
        password: Optional[str] = None,
    ) -> None:
        if self.services_controller is not None:
            self.services_controller.registerUser(case, username, password)
        else:
            raise NotImplementedByController("account registration")

    def wait_for_port(self) -> None:
        started_at = time.time()
        while not self.port_open:
            self.check_is_alive()
            time.sleep(self._port_wait_interval)
            try:
                c = socket.create_connection(("localhost", self.port), timeout=1.0)
                c.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

                # Make sure the server properly processes the disconnect.
                # Otherwise, it may still count it in LUSER and fail tests in
                # test_lusers.py (eg. this happens with Charybdis 3.5.0)
                c.sendall(b"QUIT :chkport\r\n")
                data = b""
                try:
                    while b"chkport" not in data and b"ERROR" not in data:
                        data += c.recv(4096)
                        time.sleep(0.01)

                        c.send(b" ")  # Triggers BrokenPipeError
                except (BrokenPipeError, ConnectionResetError):
                    # ircu2 cuts the connection without a message if registration
                    # is not complete.
                    pass
                except socket.timeout:
                    # irc2 just keeps it open
                    pass

                c.close()
                self.port_open = True
            except ConnectionRefusedError:
                if time.time() - started_at >= 60:
                    # waited for 60 seconds, giving up
                    raise

    def wait_for_services(self) -> None:
        assert self.services_controller
        self.services_controller.wait_for_services()

    def terminate(self) -> None:
        if self.services_controller is not None:
            self.services_controller.terminate()  # type: ignore
        super().terminate()  # type: ignore

    def kill(self) -> None:
        if self.services_controller is not None:
            self.services_controller.kill()  # type: ignore
        super().kill()


class BaseServicesController(_BaseController):
    def __init__(
        self,
        test_config: TestCaseControllerConfig,
        server_controller: BaseServerController,
    ):
        super().__init__(test_config)
        self.test_config = test_config
        self.server_controller = server_controller
        self.services_up = False

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        raise NotImplementedError("BaseServerController.run()")

    def wait_for_services(self) -> None:
        if self.services_up:
            # Don't check again if they are already available
            return
        self.server_controller.wait_for_port()

        c = ClientMock(name="chkNS", show_io=True)
        c.connect(self.server_controller.hostname, self.server_controller.port)
        c.sendLine("NICK chkNS")
        c.sendLine("USER chk chk chk chk")
        time.sleep(self.server_controller.sync_sleep_time)
        got_end_of_motd = False
        while not got_end_of_motd:
            for msg in c.getMessages(synchronize=False):
                if msg.command == "PING":
                    # Hi Unreal
                    c.sendLine("PONG :" + msg.params[0])
                if msg.command in ("376", "422"):  # RPL_ENDOFMOTD / ERR_NOMOTD
                    got_end_of_motd = True

        timeout = time.time() + 10
        while True:
            c.sendLine(f"PRIVMSG {self.server_controller.nickserv} :help")

            msgs = self.getNickServResponse(c, timeout=1)
            for msg in msgs:
                if msg.command == "401":
                    # NickServ not available yet
                    pass
                elif msg.command in ("MODE", "221"):  # RPL_UMODEIS
                    pass
                elif msg.command == "396":  # RPL_VISIBLEHOST
                    pass
                elif msg.command == "NOTICE":
                    assert msg.prefix is not None
                    if "!" not in msg.prefix and "." in msg.prefix:
                        # Server notice
                        pass
                    else:
                        # NickServ is available
                        assert "nickserv" in (msg.prefix or "").lower(), msg
                        break
                else:
                    assert False, f"unexpected reply from NickServ: {msg}"
            else:
                if time.time() > timeout:
                    raise Exception("Timeout while waiting for NickServ")
                continue

            # If we're here, it means we broke from the for loop, so NickServ
            # is available and we can break again
            break

        c.sendLine("QUIT")
        c.getMessages()
        c.disconnect()
        self.services_up = True

    def getNickServResponse(self, client: Any, timeout: int = 0) -> List[Message]:
        """Wrapper aroung getMessages() that waits longer, because NickServ
        is queried asynchronously."""
        msgs: List[Message] = []
        start_time = time.time()
        while not msgs and (not timeout or start_time + timeout > time.time()):
            time.sleep(0.05)
            msgs = client.getMessages()
        return msgs

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,  # type: ignore
        username: str,
        password: Optional[str] = None,
    ) -> None:
        if not case.run_services:
            raise ValueError(
                "Attempted to register a nick, but `run_services` it not True."
            )
        assert password
        client = case.addClient(show_io=True)
        case.sendLine(client, "NICK " + username)
        case.sendLine(client, "USER r e g :user")
        while case.getRegistrationMessage(client).command != "001":
            pass
        case.getMessages(client)
        case.sendLine(
            client,
            f"PRIVMSG {self.server_controller.nickserv} "
            f":REGISTER {password} foo@example.org",
        )
        msgs = self.getNickServResponse(case.clients[client])
        if self.server_controller.software_name == "inspircd":
            assert "900" in {msg.command for msg in msgs}, msgs
        assert "NOTICE" in {msg.command for msg in msgs}, msgs
        case.sendLine(client, "QUIT")
        case.assertDisconnected(client)
