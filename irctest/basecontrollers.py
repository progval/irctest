import os
import shutil
import socket
import subprocess
import tempfile
import time

from .runner import NotImplementedByController


class ProcessStopped(Exception):
    """Raised when the controlled process stopped unexpectedly"""

    pass


class _BaseController:
    """Base class for software controllers.

    A software controller is an object that handles configuring and running
    a process (eg. a server or a client), as well as sending it instructions
    that are not part of the IRC specification."""

    def __init__(self, test_config):
        self.test_config = test_config
        self.proc = None

    def check_is_alive(self):
        self.proc.poll()
        if self.proc.returncode is not None:
            raise ProcessStopped()


class DirectoryBasedController(_BaseController):
    """Helper for controllers whose software configuration is based on an
    arbitrary directory."""

    def __init__(self, test_config):
        super().__init__(test_config)
        self.directory = None

    def kill_proc(self):
        """Terminates the controlled process, waits for it to exit, and
        eventually kills it."""
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None

    def kill(self):
        """Calls `kill_proc` and cleans the configuration."""
        if self.proc:
            self.kill_proc()
        if self.directory:
            shutil.rmtree(self.directory)

    def terminate(self):
        """Stops the process gracefully, and does not clean its config."""
        self.proc.terminate()
        self.proc.wait()
        self.proc = None

    def open_file(self, name, mode="a"):
        """Open a file in the configuration directory."""
        assert self.directory
        if os.sep in name:
            dir_ = os.path.join(self.directory, os.path.dirname(name))
            if not os.path.isdir(dir_):
                os.makedirs(dir_)
            assert os.path.isdir(dir_)
        return open(os.path.join(self.directory, name), mode)

    def create_config(self):
        """If there is no config dir, creates it and returns True.
        Else returns False."""
        if self.directory:
            return False
        else:
            self.directory = tempfile.mkdtemp()
            return True

    def gen_ssl(self):
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

    def run(self, hostname, port, auth):
        raise NotImplementedError()


class BaseServerController(_BaseController):
    """Base controller for IRC server."""

    _port_wait_interval = 0.1
    port_open = False

    def run(self, hostname, port, password, valid_metadata_keys, invalid_metadata_keys):
        raise NotImplementedError()

    def registerUser(self, case, username, password=None):
        raise NotImplementedByController("account registration")

    def wait_for_port(self):
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
