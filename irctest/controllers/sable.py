import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Optional, Sequence, Type

from irctest.basecontrollers import (
    BaseServerController,
    BaseServicesController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.cases import BaseServerTestCase
from irctest.exceptions import NoMessageException
from irctest.patma import ANYSTR

GEN_CERTS = """
mkdir -p useless_openssl_data/

cat > openssl.cnf <<EOF
[ ca ]
default_ca	= CA_default		# The default ca section

[ CA_default ]
new_certs_dir = useless_openssl_data/
database = useless_openssl_data/db
policy = policy_anything
serial = useless_openssl_data/serial
copy_extensions = copy
email_in_dn = no
rand_serial = no

[ policy_anything ]
countryName		       = optional
stateOrProvinceName	   = optional
localityName		   = optional
organizationName	   = optional
organizationalUnitName	= optional
commonName		       = supplied
emailAddress		   = optional

[ usr_cert ]
subjectAltName=subject:copy
EOF

rm -f useless_openssl_data/db
touch useless_openssl_data/db
echo 01 > useless_openssl_data/serial

# Generate CA
openssl req -x509 -nodes -newkey rsa:2048 -batch \
    -subj "/CN=Test CA" \
    -outform PEM -out ca_cert.pem \
    -keyout ca_cert.key

for server in $*; do
    openssl genrsa -traditional \
        -out $server.key \
        2048
    openssl req -nodes -batch -new \
        -addext "subjectAltName = DNS:$server" \
        -key $server.key \
        -outform PEM -out server_$server.req
    openssl ca -config openssl.cnf -days 3650 -md sha512 -batch \
        -subj /CN=$server \
        -keyfile ca_cert.key -cert ca_cert.pem \
        -in server_$server.req \
        -out $server.pem
    openssl x509 -sha1 -in $server.pem -fingerprint -noout \
        | sed "s/.*=//" | sed "s/://g" | tr '[:upper:]' '[:lower:]' > $server.pem.sha1
done

rm -r useless_openssl_data/
"""

_certs_dir = None


def certs_dir() -> Path:
    global _certs_dir
    if _certs_dir is None:
        certs_dir = tempfile.TemporaryDirectory()
        (Path(certs_dir.name) / "gen_certs.sh").write_text(GEN_CERTS)
        subprocess.run(
            ["bash", "gen_certs.sh", "My.Little.Server", "My.Little.History", "My.Little.Services"],
            cwd=certs_dir.name,
            check=True,
        )
        _certs_dir = certs_dir
    return Path(_certs_dir.name)


NETWORK_CONFIG = """
{
    "fanout": 1,
    "ca_file": "%(certs_dir)s/ca_cert.pem",

    "peers": [
        { "name": "My.Little.History", "address": "%(history_hostname)s:%(history_port)s", "fingerprint": "%(history_cert_sha1)s" },
        { "name": "My.Little.Services", "address": "%(services_hostname)s:%(services_port)s", "fingerprint": "%(services_cert_sha1)s" },
        { "name": "My.Little.Server", "address": "%(server1_hostname)s:%(server1_port)s", "fingerprint": "%(server1_cert_sha1)s" }
    ]
}
"""

NETWORK_CONFIG_CONFIG = """
{
    "object_expiry": 60,  // 1 minute

    "opers": [
        {
            "name": "operuser",
            // echo -n "operpassword" | openssl passwd -6 -stdin
            "hash": "$6$z5yA.OfGliDoi/R2$BgSsguS6bxAsPSCygDisgDw5JZuo5.88eU3Hyc7/4OaNpeKIxWGjOggeHzOl0xLiZg1vfwxXjOTFN14wG5vNI."
        }
    ],

    "alias_users": [
        %(services_alias_users)s
    ],

    "default_roles": {
        "builtin:op": [
            "always_send",
            "op_self", "op_grant", "voice_self", "voice_grant",
            "receive_op", "receive_voice", "receive_opmod",
            "topic", "kick", "set_simple_mode", "set_key",
            "rename",
            "ban_view", "ban_add", "ban_remove_any",
            "quiet_view", "quiet_add", "quiet_remove_any",
            "exempt_view", "exempt_add", "exempt_remove_any",
            "invite_self", "invite_other",
            "invex_view", "invex_add", "invex_remove_any"
        ],
        "builtin:voice": [
            "always_send",
            "voice_self",
            "receive_voice",
            "ban_view", "quiet_view"
        ],
        "builtin:all": [
            "ban_view", "quiet_view"
        ]
    },

    "debug_mode": true
}
"""

SERVICES_ALIAS_USERS = """
        {
            "nick": "ChanServ",
            "user": "ChanServ",
            "host": "services.",
            "realname": "Channel services compatibility layer",
            "command_alias": "CS"
        },
        {
            "nick": "NickServ",
            "user": "NickServ",
            "host": "services.",
            "realname": "Account services compatibility layer",
            "command_alias": "NS"
        }
"""

SERVER_CONFIG = """
{
    "server_id": 1,
    "server_name": "My.Little.Server",

    "management": {
        "address": "%(server1_management_hostname)s:%(server1_management_port)s",
        "client_ca": "%(certs_dir)s/ca_cert.pem",
        "authorised_fingerprints": [
            { "name": "user1", "fingerprint": "435bc6db9f22e84ba5d9652432154617c9509370" },
        ],
    },

    "server": {
        "listeners": [
            { "address": "%(c2s_hostname)s:%(c2s_port)s" },
        ],
    },

    "event_log": {
        "event_expiry": 300, // five minutes, for local testing
    },

    "tls_config": {
        "key_file": "%(certs_dir)s/My.Little.Server.key",
        "cert_file": "%(certs_dir)s/My.Little.Server.pem",
    },

    "node_config": {
        "listen_addr": "%(server1_hostname)s:%(server1_port)s",
        "cert_file": "%(certs_dir)s/My.Little.Server.pem",
        "key_file": "%(certs_dir)s/My.Little.Server.key",
    },

    "log": {
        "dir": "log/server1/",

        "module-levels": {
            "": "debug",
            "sable_ircd": "trace",
        },

        "targets": [
            {
                "target": "stdout",
                "level": "trace",
                "modules": [ "sable", "audit", "client_listener" ],
            },
        ],
    },
}
"""

HISTORY_SERVER_CONFIG = """
{
    "server_id": 50,
    "server_name": "My.Little.History",

    "management": {
        "address": "%(history_management_hostname)s:%(history_management_port)s",
        "client_ca": "%(certs_dir)s/ca_cert.pem",
        "authorised_fingerprints": [
            { "name": "user1", "fingerprint": "435bc6db9f22e84ba5d9652432154617c9509370" }
        ]
    },

    "server": {
        "database": "%(history_db_url)s",
        "auto_run_migrations": true,
    },

    "event_log": {
        "event_expiry": 300, // five minutes, for local testing
    },

    "tls_config": {
        "key_file": "%(certs_dir)s/My.Little.History.key",
        "cert_file": "%(certs_dir)s/My.Little.History.pem"
    },

    "node_config": {
        "listen_addr": "%(history_hostname)s:%(history_port)s",
        "cert_file": "%(certs_dir)s/My.Little.History.pem",
        "key_file": "%(certs_dir)s/My.Little.History.key"
    },

    "log": {
        "dir": "log/services/",

        "module-levels": {
            "": "debug",
            "sable_history": "trace",
        },

        "targets": [
            {
                "target": "stdout",
                "level": "trace",
                "modules": [ "sable_history" ]
            }
        ]
    }
}
"""

SERVICES_CONFIG = """
{
    "server_id": 99,
    "server_name": "My.Little.Services",

    "management": {
        "address": "%(services_management_hostname)s:%(services_management_port)s",
        "client_ca": "%(certs_dir)s/ca_cert.pem",
        "authorised_fingerprints": [
            { "name": "user1", "fingerprint": "435bc6db9f22e84ba5d9652432154617c9509370" }
        ]
    },

    "server": {
        "database": "test_database.json",
        "default_roles": {
            "builtin:founder": [
                "founder", "access_view", "access_edit", "role_view", "role_edit",
                "op_self", "op_grant",
                "voice_self", "voice_grant",
                "always_send",
                "invite_self", "invite_other",
                "receive_op", "receive_voice", "receive_opmod",
                "topic", "kick", "set_simple_mode", "set_key",
                "rename",
                "ban_view", "ban_add", "ban_remove_any",
                "quiet_view", "quiet_add", "quiet_remove_any",
                "exempt_view", "exempt_add", "exempt_remove_any",
                "invex_view", "invex_add", "invex_remove_any"
            ],
            "builtin:op": [
                "always_send",
                "receive_op", "receive_voice", "receive_opmod",
                "topic", "kick", "set_simple_mode", "set_key",
                "rename",
                "ban_view", "ban_add", "ban_remove_any",
                "quiet_view", "quiet_add", "quiet_remove_any",
                "exempt_view", "exempt_add", "exempt_remove_any",
                "invex_view", "invex_add", "invex_remove_any"
            ],
            "builtin:voice": [
                "always_send", "voice_self", "receive_voice"
            ]
        },

        "password_hash": {
            "algorithm": "bcrypt", // Only "bcrypt" is supported for now
            "cost": 4,  // Exponentially faster than the default 12
        },

    },

    "event_log": {
        "event_expiry": 300, // five minutes, for local testing
    },

    "tls_config": {
        "key_file": "%(certs_dir)s/My.Little.Services.key",
        "cert_file": "%(certs_dir)s/My.Little.Services.pem"
    },

    "node_config": {
        "listen_addr": "%(services_hostname)s:%(services_port)s",
        "cert_file": "%(certs_dir)s/My.Little.Services.pem",
        "key_file": "%(certs_dir)s/My.Little.Services.key"
    },

    "log": {
        "dir": "log/services/",

        "module-levels": {
            "": "debug"
        },

        "targets": [
            {
                "target": "stdout",
                "level": "debug",
                "modules": [ "sable_services" ]
            }
        ]
    }
}
"""


class SableController(BaseServerController, DirectoryBasedController):
    software_name = "Sable"
    supported_sasl_mechanisms = {"PLAIN"}
    sync_sleep_time = 0.1
    """Sable processes commands very quickly, but responses for commands changing the
    state may be sent after later commands for messages which don't."""

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
        if password is not None:
            raise NotImplementedByController("PASS command")
        if ssl:
            raise NotImplementedByController("SSL")
        if self.test_config.account_registration_before_connect:
            raise NotImplementedByController("account-registration with before-connect")
        if self.test_config.account_registration_requires_email:
            raise NotImplementedByController("account-registration with email-required")

        assert self.proc is None
        self.port = port
        self.create_config()

        assert self.directory

        (self.directory / "configs").mkdir()

        c2s_hostname = hostname
        c2s_port = port
        del hostname, port
        # base controller expects this to check for NickServ presence itself
        self.hostname = c2s_hostname
        self.port = c2s_port

        (server1_hostname, server1_port) = self.get_hostname_and_port()
        (services_hostname, services_port) = self.get_hostname_and_port()
        (history_hostname, history_port) = self.get_hostname_and_port()

        # Sable requires inbound connections to match the configured hostname,
        # so we can't configure 0.0.0.0
        server1_hostname = history_hostname = services_hostname = "127.0.0.1"

        (
            server1_management_hostname,
            server1_management_port,
        ) = self.get_hostname_and_port()
        (
            services_management_hostname,
            services_management_port,
        ) = self.get_hostname_and_port()
        (
            history_management_hostname,
            history_management_port,
        ) = self.get_hostname_and_port()

        self.template_vars = dict(
            certs_dir=certs_dir(),
            c2s_hostname=c2s_hostname,
            c2s_port=c2s_port,
            server1_hostname=server1_hostname,
            server1_port=server1_port,
            server1_cert_sha1=(certs_dir() / "My.Little.Server.pem.sha1")
            .read_text()
            .strip(),
            server1_management_hostname=server1_management_hostname,
            server1_management_port=server1_management_port,
            services_hostname=services_hostname,
            services_port=services_port,
            services_cert_sha1=(certs_dir() / "My.Little.Services.pem.sha1")
            .read_text()
            .strip(),
            services_management_hostname=services_management_hostname,
            services_management_port=services_management_port,
            services_alias_users=SERVICES_ALIAS_USERS if run_services else "",
            history_hostname=history_hostname,
            history_port=history_port,
            history_cert_sha1=(certs_dir() / "My.Little.History.pem.sha1")
            .read_text()
            .strip(),
            history_management_hostname=history_management_hostname,
            history_management_port=history_management_port,
        )

        with self.open_file("configs/network.conf") as fd:
            fd.write(NETWORK_CONFIG % self.template_vars)
        with self.open_file("configs/network_config.conf") as fd:
            fd.write(NETWORK_CONFIG_CONFIG % self.template_vars)
        with self.open_file("configs/server1.conf") as fd:
            fd.write(SERVER_CONFIG % self.template_vars)

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = self.execute(
            [
                *faketime_cmd,
                "sable_ircd",
                "--foreground",
                "--server-conf",
                self.directory / "configs/server1.conf",
                "--network-conf",
                self.directory / "configs/network.conf",
                "--bootstrap-network",
                self.directory / "configs/network_config.conf",
            ],
            cwd=self.directory,
            preexec_fn=os.setsid,
            env={"RUST_BACKTRACE": "1", **os.environ},
        )
        self.pgroup_id = os.getpgid(self.proc.pid)

        if run_services:
            self.services_controller = SableServicesController(self.test_config, self)
            self.services_controller.faketime_cmd = faketime_cmd
            self.services_controller.run(
                protocol="sable",
                server_hostname=services_hostname,
                server_port=services_port,
            )

        if self.test_config.sable_history_server:
            self.history_controller = SableHistoryController(self.test_config, self)
            self.history_controller.faketime_cmd = faketime_cmd
            self.history_controller.run(
                protocol="sable",
                server_hostname=history_hostname,
                server_port=history_port,
            )

    def kill_proc(self) -> None:
        os.killpg(self.pgroup_id, signal.SIGKILL)
        super().kill_proc()

    def registerUser(
        self,
        case: BaseServerTestCase,  # type: ignore
        username: str,
        password: Optional[str] = None,
    ) -> None:
        # XXX: Move this somewhere else when
        # https://github.com/ircv3/ircv3-specifications/pull/152 becomes
        # part of the specification
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
            f"REGISTER * * {password}",
        )
        for _ in range(100):
            time.sleep(0.1)
            try:
                msg = case.getMessage(client)
            except NoMessageException:
                continue
            case.assertMessageMatch(
                msg, command="REGISTER", params=["SUCCESS", username, ANYSTR]
            )
            break
        else:
            raise NoMessageException()
        case.sendLine(client, "QUIT")
        case.assertDisconnected(client)


class SableServicesController(BaseServicesController):
    server_controller: SableController
    software_name = "Sable Services"

    faketime_cmd: Sequence[str]

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        assert protocol == "sable"
        assert self.server_controller.directory is not None

        with self.server_controller.open_file("configs/services.conf") as fd:
            fd.write(SERVICES_CONFIG % self.server_controller.template_vars)

        self.proc = self.execute(
            [
                *self.faketime_cmd,
                "sable_services",
                "--foreground",
                "--server-conf",
                self.server_controller.directory / "configs/services.conf",
                "--network-conf",
                self.server_controller.directory / "configs/network.conf",
            ],
            cwd=self.server_controller.directory,
            preexec_fn=os.setsid,
            env={"RUST_BACKTRACE": "1", **os.environ},
        )
        self.pgroup_id = os.getpgid(self.proc.pid)

    def kill_proc(self) -> None:
        os.killpg(self.pgroup_id, signal.SIGKILL)
        super().kill_proc()


class SableHistoryController(BaseServicesController):
    server_controller: SableController
    software_name = "Sable History Server"
    faketime_cmd: Sequence[str]

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        assert protocol == "sable"
        assert self.server_controller.directory is not None
        history_db_url=os.environ.get("PIFPAF_POSTGRESQL_URL") or os.environ.get("IRCTEST_POSTGRESQL_URL")
        assert history_db_url, (
            "Cannot find a postgresql database to use as backend for sable_history. "
            "Either set the IRCTEST_POSTGRESQL_URL env var to a libpq URL, or "
            "run `pip3 install pifpaf` and wrap irctest in a pifpaf call (ie. "
            "pifpaf run postgresql -- pytest --controller=irctest.controllers.sable ...)"
        )

        with self.server_controller.open_file("configs/history_server.conf") as fd:
            fd.write(HISTORY_SERVER_CONFIG % {
                **self.server_controller.template_vars,
                "history_db_url": history_db_url,
            })

        self.proc = self.execute(
            [
                *self.faketime_cmd,
                "sable_history",
                "--foreground",
                "--server-conf",
                self.server_controller.directory / "configs/history_server.conf",
                "--network-conf",
                self.server_controller.directory / "configs/network.conf",
            ],
            cwd=self.server_controller.directory,
            preexec_fn=os.setsid,
            env={"RUST_BACKTRACE": "1", **os.environ},
        )
        self.pgroup_id = os.getpgid(self.proc.pid)

    def kill_proc(self) -> None:
        os.killpg(self.pgroup_id, signal.SIGKILL)
        super().kill_proc()


def get_irctest_controller_class() -> Type[SableController]:
    return SableController
