import copy
import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Set, Type, Union

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.cases import BaseServerTestCase

BASE_CONFIG = {
    "network": {"name": "ErgoTest"},
    "server": {
        "name": "My.Little.Server",
        "listeners": {},
        "max-sendq": "16k",
        "connection-limits": {
            "enabled": True,
            "cidr-len-ipv4": 32,
            "cidr-len-ipv6": 64,
            "ips-per-subnet": 1,
            "exempted": ["localhost"],
        },
        "connection-throttling": {
            "enabled": True,
            "cidr-len-ipv4": 32,
            "cidr-len-ipv6": 64,
            "ips-per-subnet": 16,
            "duration": "10m",
            "max-connections": 1,
            "ban-duration": "10m",
            "ban-message": "Try again later",
            "exempted": ["localhost"],
        },
        "lookup-hostnames": False,
        "enforce-utf8": True,
        "relaymsg": {"enabled": True, "separators": "/", "available-to-chanops": True},
        "compatibility": {
            "allow-truncation": False,
        },
    },
    "accounts": {
        "authentication-enabled": True,
        "advertise-scram": True,
        "multiclient": {
            "allowed-by-default": True,
            "enabled": True,
            "always-on": "disabled",
        },
        "registration": {
            "bcrypt-cost": 4,
            "enabled": True,
            "enabled-callbacks": ["none"],
            "verify-timeout": "120h",
        },
        "nick-reservation": {
            "enabled": True,
            "method": "strict",
        },
    },
    "channels": {"registration": {"enabled": True}},
    "datastore": {"path": None},
    "limits": {
        "awaylen": 200,
        "chan-list-modes": 60,
        "channellen": 64,
        "kicklen": 390,
        "linelen": {"rest": 2048},
        "monitor-entries": 100,
        "nicklen": 32,
        "topiclen": 390,
        "whowas-entries": 100,
        "multiline": {"max-bytes": 4096, "max-lines": 32},
    },
    "history": {
        "enabled": True,
        "channel-length": 128,
        "client-length": 128,
        "chathistory-maxmessages": 100,
        "tagmsg-storage": {
            "default": False,
            "whitelist": ["+draft/persist", "+persist"],
        },
    },
    "oper-classes": {
        "server-admin": {
            "title": "Server Admin",
            "capabilities": [
                "oper:local_kill",
                "oper:local_ban",
                "oper:local_unban",
                "nofakelag",
                "oper:remote_kill",
                "oper:remote_ban",
                "oper:remote_unban",
                "oper:rehash",
                "oper:die",
                "accreg",
                "sajoin",
                "samode",
                "vhosts",
                "chanreg",
                "relaymsg",
            ],
        }
    },
    "opers": {
        "operuser": {
            "class": "server-admin",
            "whois-line": "is a server admin",
            # "operpassword"
            "password": "$2a$04$bKb6k5A6yuFA2wx.iJtxcuT2dojHQAjHd5ZPK/I2sjJml7p4spxjG",
        }
    },
}

LOGGING_CONFIG = {"logging": [{"method": "stderr", "level": "debug", "type": "*"}]}


def hash_password(password: Union[str, bytes]) -> str:
    if isinstance(password, str):
        password = password.encode("utf-8")
    # simulate entry of password and confirmation:
    input_ = password + b"\n" + password + b"\n"
    p = subprocess.Popen(
        ["ergo", "genpasswd"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    out, _ = p.communicate(input_)
    return out.decode("utf-8")


class ErgoController(BaseServerController, DirectoryBasedController):
    software_name = "Ergo"
    _port_wait_interval = 0.01
    supported_sasl_mechanisms = {"PLAIN", "SCRAM-SHA-256"}
    supports_sts = True
    extban_mute_char = "m"
    mysql_proc: Optional[subprocess.Popen] = None

    def create_config(self) -> None:
        super().create_config()
        with self.open_file("ircd.yaml"):
            pass

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        run_services: bool,
        valid_metadata_keys: Optional[Set[str]] = None,
        invalid_metadata_keys: Optional[Set[str]] = None,
        restricted_metadata_keys: Optional[Set[str]] = None,
        faketime: Optional[str],
        config: Optional[Any] = None,
    ) -> None:
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                "Defining valid and invalid METADATA keys."
            )

        self.create_config()
        if config is None:
            config = copy.deepcopy(BASE_CONFIG)

        assert self.directory

        enable_chathistory = self.test_config.chathistory
        enable_roleplay = self.test_config.ergo_roleplay
        if enable_chathistory or enable_roleplay:
            self.addDatabaseToConfig(config)

        if enable_roleplay:
            config["roleplay"] = {"enabled": True}

        if self.test_config.ergo_config:
            self.test_config.ergo_config(config)

        self.port = port
        bind_address = "127.0.0.1:%s" % (port,)
        listener_conf = None  # plaintext
        if ssl:
            self.key_path = os.path.join(self.directory, "ssl.key")
            self.pem_path = os.path.join(self.directory, "ssl.pem")
            listener_conf = {"tls": {"cert": self.pem_path, "key": self.key_path}}
        config["server"]["listeners"][bind_address] = listener_conf  # type: ignore

        config["datastore"]["path"] = os.path.join(  # type: ignore
            self.directory, "ircd.db"
        )

        if password is not None:
            config["server"]["password"] = hash_password(password)  # type: ignore

        assert self.proc is None

        self._config_path = os.path.join(self.directory, "server.yml")
        self._config = config
        self._write_config()
        subprocess.call(["ergo", "initdb", "--conf", self._config_path, "--quiet"])
        subprocess.call(["ergo", "mkcerts", "--conf", self._config_path, "--quiet"])

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = subprocess.Popen(
            [*faketime_cmd, "ergo", "run", "--conf", self._config_path, "--quiet"]
        )

    def terminate(self) -> None:
        if self.mysql_proc is not None:
            self.mysql_proc.terminate()
        super().terminate()

    def kill(self) -> None:
        if self.mysql_proc is not None:
            self.mysql_proc.kill()
        super().kill()

    def wait_for_services(self) -> None:
        # Nothing to wait for, they start at the same time as Ergo.
        pass

    def registerUser(
        self,
        case: BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        # XXX: Move this somewhere else when
        # https://github.com/ircv3/ircv3-specifications/pull/152 becomes
        # part of the specification
        if not case.run_services:
            # Ergo does not actually need this, but other controllers do, so we
            # are checking it here as well for tests that aren't tested with other
            # controllers.
            raise ValueError(
                "Attempted to register a nick, but `run_services` it not True."
            )
        client = case.addClient(show_io=False)
        case.sendLine(client, "CAP LS 302")
        case.sendLine(client, "NICK " + username)
        case.sendLine(client, "USER r e g :user")
        case.sendLine(client, "CAP END")
        while case.getRegistrationMessage(client).command != "001":
            pass
        case.getMessages(client)
        assert password
        case.sendLine(client, "NS REGISTER " + password)
        msg = case.getMessage(client)
        assert msg.params == [username, "Account created"]
        case.sendLine(client, "QUIT")
        case.assertDisconnected(client)

    def _write_config(self) -> None:
        with open(self._config_path, "w") as fd:
            json.dump(self._config, fd)

    def baseConfig(self) -> Dict:
        return copy.deepcopy(BASE_CONFIG)

    def getConfig(self) -> Dict:
        return copy.deepcopy(self._config)

    def addLoggingToConfig(self, config: Optional[Dict] = None) -> Dict:
        if config is None:
            config = self.baseConfig()
        config.update(LOGGING_CONFIG)
        return config

    def addDatabaseToConfig(self, config: Dict) -> None:
        history_backend = os.environ.get("ERGO_HISTORY_BACKEND", "memory")
        if history_backend == "memory":
            # nothing to do, this is the default
            pass
        elif history_backend == "mysql":
            socket_path = self.startMysql()
            self.createMysqlDatabase(socket_path, "ergo_history")
            config["datastore"]["mysql"] = {
                "enabled": True,
                "socket-path": socket_path,
                "history-database": "ergo_history",
                "timeout": "3s",
            }
            config["history"]["persistent"] = {
                "enabled": True,
                "unregistered-channels": True,
                "registered-channels": "opt-out",
                "direct-messages": "opt-out",
            }
        else:
            raise ValueError(
                f"Invalid $ERGO_HISTORY_BACKEND value: {history_backend}. "
                f"It should be 'memory' (the default) or 'mysql'"
            )

    def startMysql(self) -> str:
        """Starts a new MySQL server listening on a UNIX socket, returns the socket
        path"""
        # Function based on pifpaf's MySQL driver:
        # https://github.com/jd/pifpaf/blob/3.1.5/pifpaf/drivers/mysql.py
        assert self.directory
        mysql_dir = os.path.join(self.directory, "mysql")
        socket_path = os.path.join(mysql_dir, "mysql.socket")
        os.mkdir(mysql_dir)

        print("Starting MySQL...")
        try:
            subprocess.check_call(
                [
                    "mysqld",
                    "--no-defaults",
                    "--tmpdir=" + mysql_dir,
                    "--initialize-insecure",
                    "--datadir=" + mysql_dir,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            # Initialize the old way
            subprocess.check_call(
                [
                    "mysql_install_db",
                    "--no-defaults",
                    "--tmpdir=" + mysql_dir,
                    "--datadir=" + mysql_dir,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        self.mysql_proc = subprocess.Popen(
            [
                "mysqld",
                "--no-defaults",
                "--tmpdir=" + mysql_dir,
                "--datadir=" + mysql_dir,
                "--socket=" + socket_path,
                "--skip-networking",
                "--skip-grant-tables",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        mysql_stdout = self.mysql_proc.stdout
        assert mysql_stdout is not None  # for mypy...
        lines: List[bytes] = []
        while self.mysql_proc.returncode is None:
            line = mysql_stdout.readline()
            lines.append(lines)
            if b"mysqld: ready for connections." in line:
                break
        assert self.mysql_proc.returncode is None, (
            "MySQL unexpected stopped: " + b"\n".join(lines).decode()
        )
        print("MySQL started")

        return socket_path

    def createMysqlDatabase(self, socket_path: str, database_name: str) -> None:
        subprocess.check_call(
            [
                "mysql",
                "--no-defaults",
                "-S",
                socket_path,
                "-e",
                f"CREATE DATABASE {database_name};",
            ]
        )

    def rehash(self, case: BaseServerTestCase, config: Dict) -> None:
        self._config = config
        self._write_config()
        client = "operator_for_rehash"
        case.connectClient(nick=client, name=client)
        case.sendLine(client, "OPER operuser operpassword")
        case.sendLine(client, "REHASH")
        case.getMessages(client)
        case.sendLine(client, "QUIT")
        case.assertDisconnected(client)

    def enable_debug_logging(self, case: BaseServerTestCase) -> None:
        config = self.getConfig()
        config.update(LOGGING_CONFIG)
        self.rehash(case, config)


def get_irctest_controller_class() -> Type[ErgoController]:
    return ErgoController
