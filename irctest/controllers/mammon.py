import os
import subprocess
from typing import Optional, Set, Type

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.cases import BaseServerTestCase

TEMPLATE_CONFIG = """
clients:
  # ping_frequency - client ping frequency
  ping_frequency:
    minutes: 1000

  # ping_timeout - ping timeout length
  ping_timeout:
    seconds: 10
data:
  format: json
  filename: {directory}/data.json
  save_frequency:
    minutes: 5
extensions:
- mammon.ext.rfc1459.42
- mammon.ext.rfc1459.ident
- mammon.ext.ircv3.account_notify
- mammon.ext.ircv3.server_time
- mammon.ext.ircv3.echo_message
- mammon.ext.ircv3.register
- mammon.ext.ircv3.sasl
- mammon.ext.misc.nopost
metadata:
  restricted_keys:
{restricted_keys}
  whitelist:
{authorized_keys}
monitor:
  limit: 20
motd:
  - "Hi"
limits:
  foo: bar
listeners:
- {{"host": "{hostname}", "port": {port}, "ssl": false}}
logs:
  {{
  }}
register:
  enabled_callbacks:
  - none
  verify_timeout:
    days: 1
roles:
  "placeholder":
    title: "Just a placeholder"
server:
  name: MyLittleServer
  network: MyLittleNetwork
  recvq_len: 20
"""


def make_list(list_: Set[str]) -> str:
    return "\n".join(map("  - {}".format, list_))


class MammonController(BaseServerController, DirectoryBasedController):
    software_name = "Mammon"
    supported_sasl_mechanisms = {"PLAIN", "ECDSA-NIST256P-CHALLENGE"}

    def create_config(self) -> None:
        super().create_config()
        with self.open_file("server.conf"):
            pass

    def kill_proc(self) -> None:
        # Mammon does not seem to handle SIGTERM very well
        assert self.proc
        self.proc.kill()

    def run(
        self,
        hostname: str,
        port: int,
        *,
        password: Optional[str],
        ssl: bool,
        valid_metadata_keys: Optional[Set[str]] = None,
        invalid_metadata_keys: Optional[Set[str]] = None,
        restricted_metadata_keys: Optional[Set[str]] = None,
    ) -> None:
        if password is not None:
            raise NotImplementedByController("PASS command")
        if ssl:
            raise NotImplementedByController("SSL")
        assert self.proc is None
        self.port = port
        self.create_config()
        with self.open_file("server.yml") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    directory=self.directory,
                    hostname=hostname,
                    port=port,
                    authorized_keys=make_list(valid_metadata_keys or set()),
                    restricted_keys=make_list(restricted_metadata_keys or set()),
                )
            )
        # with self.open_file('server.yml', 'r') as fd:
        #    print(fd.read())
        assert self.directory
        self.proc = subprocess.Popen(
            [
                "mammond",
                "--nofork",  # '--debug',
                "--config",
                os.path.join(self.directory, "server.yml"),
            ]
        )

    def registerUser(
        self,
        case: BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        # XXX: Move this somewhere else when
        # https://github.com/ircv3/ircv3-specifications/pull/152 becomes
        # part of the specification
        client = case.addClient(show_io=False)
        case.sendLine(client, "CAP LS 302")
        case.sendLine(client, "NICK registration_user")
        case.sendLine(client, "USER r e g :user")
        case.sendLine(client, "CAP END")
        while case.getRegistrationMessage(client).command != "001":
            pass
        list(case.getMessages(client))
        case.sendLine(client, "REG CREATE {} passphrase {}".format(username, password))
        msg = case.getMessage(client)
        assert msg.command == "920", msg
        list(case.getMessages(client))
        case.removeClient(client)


def get_irctest_controller_class() -> Type[MammonController]:
    return MammonController
