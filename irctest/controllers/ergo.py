import copy
import json
import os
import subprocess
from typing import Any, Dict, Optional, Set, Type, Union

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.cases import BaseServerTestCase

OPER_PWD = "frenchfries"

BASE_CONFIG = {
    "network": {"name": "ErgoTest"},
    "server": {
        "name": "ergo.test",
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
        "enforce-utf8": True,
        "relaymsg": {"enabled": True, "separators": "/", "available-to-chanops": True},
        "compatibility": {
            "allow-truncation": False,
        },
    },
    "accounts": {
        "authentication-enabled": True,
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
            "additional-nick-limit": 2,
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
        "root": {
            "class": "server-admin",
            "whois-line": "is a server admin",
            # OPER_PWD
            "password": "$2a$04$3GzUZB5JapaAbwn7sogpOu9NSiLOgnozVllm2e96LiNPrm61ZsZSq",
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
    supported_sasl_mechanisms = {"PLAIN"}
    supports_sts = True

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
            config = self.addMysqlToConfig(config)

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
        self.proc = subprocess.Popen(
            ["ergo", "run", "--conf", self._config_path, "--quiet"]
        )

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

    def addMysqlToConfig(self, config: Optional[Dict] = None) -> Dict:
        mysql_password = os.getenv("MYSQL_PASSWORD")
        if config is None:
            config = self.baseConfig()
        if not mysql_password:
            return config
        config["datastore"]["mysql"] = {
            "enabled": True,
            "host": "localhost",
            "user": "ergo",
            "password": mysql_password,
            "history-database": "ergo_history",
            "timeout": "3s",
        }
        config["accounts"]["multiclient"] = {
            "enabled": True,
            "allowed-by-default": True,
            "always-on": "disabled",
        }
        config["history"]["persistent"] = {
            "enabled": True,
            "unregistered-channels": True,
            "registered-channels": "opt-out",
            "direct-messages": "opt-out",
        }
        return config

    def rehash(self, case: BaseServerTestCase, config: Dict) -> None:
        self._config = config
        self._write_config()
        client = "operator_for_rehash"
        case.connectClient(nick=client, name=client)
        case.sendLine(client, "OPER root %s" % (OPER_PWD,))
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
