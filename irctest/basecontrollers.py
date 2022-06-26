from __future__ import annotations

import dataclasses
import os
import shutil
import socket
import subprocess
import tempfile
import time
from typing import IO, Any, Callable, Dict, List, Optional, Set, Tuple, Type

import irctest

from . import authentication, tls
from .client_mock import ClientMock
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

    def __init__(self, test_config: TestCaseControllerConfig):
        self.test_config = test_config
        self.proc = None

    def check_is_alive(self) -> None:
        assert self.proc
        self.proc.poll()
        if self.proc.returncode is not None:
            raise ProcessStopped()

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


class DirectoryBasedController(_BaseController):
    """Helper for controllers whose software configuration is based on an
    arbitrary directory."""

    directory: Optional[str]

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
            dir_ = os.path.join(self.directory, os.path.dirname(name))
            if not os.path.isdir(dir_):
                os.makedirs(dir_)
            assert os.path.isdir(dir_)
        return open(os.path.join(self.directory, name), mode)

    def create_config(self) -> None:
        if not self.directory:
            self.directory = tempfile.mkdtemp()

    def gen_ssl(self) -> None:
        assert self.directory
        self.csr_path = os.path.join(self.directory, "ssl.csr")
        self.key_path = os.path.join(self.directory, "ssl.key")
        self.pem_path = os.path.join(self.directory, "ssl.pem")
        self.dh_path = os.path.join(self.directory, "dh.pem")
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
        subprocess.check_output(
            [self.openssl_bin, "dhparam", "-out", self.dh_path, "128"],
            stderr=subprocess.DEVNULL,
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

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.faketime_enabled = False

    def get_hostname_and_port(self) -> Tuple[str, int]:
        return find_hostname_and_port()

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        run_services: bool,
        valid_metadata_keys: Optional[Set[str]],
        invalid_metadata_keys: Optional[Set[str]],
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
                except BrokenPipeError:
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
        for msg in c.getMessages(synchronize=False):
            if msg.command == "PING":
                # Hi Unreal
                c.sendLine("PONG :" + msg.params[0])
        c.getMessages()

        timeout = time.time() + 5
        while True:
            c.sendLine(f"PRIVMSG {self.server_controller.nickserv} :HELP")
            msgs = self.getNickServResponse(c)
            for msg in msgs:
                if msg.command == "401":
                    # NickServ not available yet
                    pass
                elif msg.command == "NOTICE":
                    # NickServ is available
                    assert "nickserv" in (msg.prefix or "").lower(), msg
                    print("breaking")
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

    def getNickServResponse(self, client: Any) -> List[Message]:
        """Wrapper aroung getMessages() that waits longer, because NickServ
        is queried asynchronously."""
        msgs: List[Message] = []
        while not msgs:
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
