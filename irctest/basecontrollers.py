from __future__ import annotations

import dataclasses
import os
import shutil
import socket
import subprocess
import tempfile
import time
from typing import IO, Any, Callable, Dict, Optional, Set

import irctest

from . import authentication, tls
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

    _port_wait_interval = 0.1
    port_open = False
    port: int

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        valid_metadata_keys: Optional[Set[str]],
        invalid_metadata_keys: Optional[Set[str]],
    ) -> None:
        raise NotImplementedError()

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,  # type: ignore
        username: str,
        password: Optional[str] = None,
    ) -> None:
        raise NotImplementedByController("account registration")

    def wait_for_port(self) -> None:
        while not self.port_open:
            self.check_is_alive()
            time.sleep(self._port_wait_interval)
            try:
                c = socket.create_connection(("localhost", self.port), timeout=1.0)
                c.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

                # Make sure the server properly processes the disconnect.
                # Otherwise, it may still count it in LUSER and fail tests in
                # test_lusers.py (eg. this happens with Charybdis 3.5.0)
                c.send(b"QUIT :chkport\r\n")
                data = b""
                while b"chkport" not in data:
                    data += c.recv(1024)

                c.close()
                self.port_open = True
            except Exception:
                continue
