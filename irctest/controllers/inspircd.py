import os
import subprocess
from typing import Optional, Set, Type

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)
from irctest.irc_utils.junkdrawer import find_hostname_and_port

TEMPLATE_CONFIG = """
# Clients:
<bind address="{hostname}" port="{port}" type="clients">
{ssl_config}
<connect allow="*"
    resolvehostnames="no" # Faster
    recvq="40960" # Needs to be larger than a valid message with tags
    timeout="10"  # So tests don't hang too long
    {password_field}>

<options casemapping="ascii">

# Services:
<bind address="{services_hostname}" port="{services_port}" type="servers">
<link name="services.example.org"
    ipaddr="{services_hostname}"
    port="{services_port}"
    allowmask="*"
    recvpass="password"
    sendpass="password"
    >
<module name="spanningtree">
<module name="services_account">
<module name="hidechans">  # Anope errors when missing
<module name="svshold">  # Atheme raises a warning when missing
<sasl requiressl="no"
      target="services.example.org">

# Protocol:
<module name="botmode">
<module name="cap">
<module name="ircv3">
<module name="ircv3_accounttag">
<module name="ircv3_batch">
<module name="ircv3_capnotify">
<module name="ircv3_ctctags">
<module name="ircv3_echomessage">
<module name="ircv3_invitenotify">
<module name="ircv3_labeledresponse">
<module name="ircv3_msgid">
<module name="ircv3_servertime">
<module name="monitor">
<module name="m_muteban">  # for testing mute extbans
<module name="namesx"> # For multi-prefix
<module name="sasl">

# Misc:
<log method="file" type="*" level="debug" target="/tmp/ircd-{port}.log">
<server name="My.Little.Server" description="testnet" id="000" network="testnet">
"""

TEMPLATE_SSL_CONFIG = """
<module name="ssl_openssl">
<openssl certfile="{pem_path}" keyfile="{key_path}" dhfile="{dh_path}" hash="sha1">
"""


class InspircdController(BaseServerController, DirectoryBasedController):
    software_name = "InspIRCd"
    supported_sasl_mechanisms = {"PLAIN"}
    supports_sts = False
    extban_mute_char = "m"

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
        valid_metadata_keys: Optional[Set[str]] = None,
        invalid_metadata_keys: Optional[Set[str]] = None,
        restricted_metadata_keys: Optional[Set[str]] = None,
    ) -> None:
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                "Defining valid and invalid METADATA keys."
            )
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()
        (services_hostname, services_port) = find_hostname_and_port()

        password_field = 'password="{}"'.format(password) if password else ""

        if ssl:
            self.gen_ssl()
            ssl_config = TEMPLATE_SSL_CONFIG.format(
                key_path=self.key_path, pem_path=self.pem_path, dh_path=self.dh_path
            )
        else:
            ssl_config = ""

        with self.open_file("server.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    services_hostname=services_hostname,
                    services_port=services_port,
                    password_field=password_field,
                    ssl_config=ssl_config,
                )
            )
        assert self.directory
        self.proc = subprocess.Popen(
            [
                "inspircd",
                "--nofork",
                "--config",
                os.path.join(self.directory, "server.conf"),
            ],
            stdout=subprocess.DEVNULL,
        )

        if run_services:
            self.wait_for_port()
            self.services_controller = self.services_controller_class(
                self.test_config, self
            )
            self.services_controller.run(
                protocol="inspircd3",
                server_hostname=services_hostname,
                server_port=services_port,
            )


def get_irctest_controller_class() -> Type[InspircdController]:
    return InspircdController
