import copy
import json
import os
import subprocess
from typing import Any, Dict, Optional, Type, Union

from irctest.basecontrollers import BaseServerController, DirectoryBasedController
from irctest.cases import BaseServerTestCase
from irctest.specifications import Capabilities, OptionalBehaviors

# ratified caps we want everyone to request, ideally
BASE_CAPS = (
    "sasl",
    "server-time",
    "message-tags",
    "echo-message",
    "batch",
    "labeled-response",
    "account-tag",
)

BASE_CONFIG = {
    "network": {"name": "ErgoTest"},
    "server": {
        "name": "My.Little.Server",
        "listeners": {},
        "max-sendq": "16k",
        "casemapping": "ascii",
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
            "always-on": "opt-in",
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
        "login-throttling": {
            "enabled": True,
            "duration": "1m",
            "max-attempts": 3,
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
        "retention": {
            "allow-individual-delete": True,
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
    "metadata": {
        "enabled": True,
        "max-subs": 100,
        "max-keys": 1000,
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
    return out.decode("utf-8").strip()


class ErgoController(BaseServerController, DirectoryBasedController):
    software_name = "Ergo"
    _port_wait_interval = 0.01
    supported_sasl_mechanisms = {"PLAIN", "SCRAM-SHA-256"}
    supports_sts = True
    extban_mute_char = "m"

    capabilities = frozenset(
        (
            Capabilities.ACCOUNT_NOTIFY,
            Capabilities.ACCOUNT_TAG,
            Capabilities.AWAY_NOTIFY,
            Capabilities.BATCH,
            Capabilities.ECHO_MESSAGE,
            Capabilities.EXTENDED_JOIN,
            Capabilities.EXTENDED_MONITOR,
            Capabilities.LABELED_RESPONSE,
            Capabilities.MESSAGE_TAGS,
            Capabilities.MULTILINE,
            Capabilities.MULTI_PREFIX,
            Capabilities.SERVER_TIME,
            Capabilities.SETNAME,
        ),
    )

    optional_behaviors = frozenset(
        (
            OptionalBehaviors.BAN_EXCEPTION_MODE,
            OptionalBehaviors.CAP_REQ_MINUS,
            OptionalBehaviors.INVITE_EXCEPTION_MODE,
            OptionalBehaviors.MULTI_JOIN,
            OptionalBehaviors.MULTI_PRIVMSG,
            OptionalBehaviors.NO_CTCP,
            OptionalBehaviors.SASL_AFTER_REGISTRATION,
            # OptionalBehaviors.SASL_REAUTHENTICATION is NOT supported :-)
        )
    )

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
        faketime: Optional[str],
        config: Optional[Any] = None,
    ) -> None:
        self.create_config()
        if config is None:
            config = copy.deepcopy(BASE_CONFIG)

        if self.debug_mode:
            config = self.addLoggingToConfig(config)

        assert self.directory

        enable_chathistory = self.test_config.chathistory
        enable_roleplay = self.test_config.ergo_roleplay
        if enable_chathistory or enable_roleplay:
            config = self.addMysqlToConfig(config)

        if enable_roleplay:
            config["roleplay"] = {"enabled": True}

        if self.test_config.account_registration_before_connect:
            config["accounts"]["registration"]["allow-before-connect"] = True  # type: ignore
        if self.test_config.account_registration_requires_email:
            config["accounts"]["registration"]["email-verification"] = {  # type: ignore
                "enabled": True,
                "sender": "test@example.com",
                "require-tls": True,
                "helo-domain": "example.com",
            }

        if self.test_config.ergo_config:
            self.test_config.ergo_config(config)

        self.port = port
        bind_address = "127.0.0.1:%s" % (port,)
        listener_conf = None  # plaintext
        if ssl:
            self.key_path = self.directory / "ssl.key"
            self.pem_path = self.directory / "ssl.pem"
            listener_conf = {"tls": {"cert": self.pem_path, "key": self.key_path}}
        config["server"]["listeners"][bind_address] = listener_conf  # type: ignore

        config["datastore"]["path"] = str(self.directory / "ircd.db")  # type: ignore

        if password is not None:
            config["server"]["password"] = hash_password(password)  # type: ignore

        assert self.proc is None

        self._config_path = self.directory / "server.yml"
        self._config = config
        self._write_config()
        subprocess.call(["ergo", "initdb", "--conf", self._config_path, "--quiet"])
        subprocess.call(["ergo", "mkcerts", "--conf", self._config_path, "--quiet"])

        self._start()

    def _start(self) -> None:
        args = ["ergo", "run", "--conf", str(self._config_path)]
        if not self.debug_mode:
            args.append("--quiet")
        self.proc = self.execute(args)

    def restart(self) -> None:
        self.kill_proc()
        self.port_open = False
        self._start()
        self.wait_for_port()

    def wait_for_services(self) -> None:
        # Nothing to wait for, they start at the same time as Ergo.
        pass

    def registerUser(
        self,
        case: BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
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
        case.sendLine(client, "OPER operuser operpassword")
        case.sendLine(client, "REHASH")
        case.getMessages(client)
        case.sendLine(client, "QUIT")
        case.assertDisconnected(client)


def get_irctest_controller_class() -> Type[ErgoController]:
    return ErgoController
