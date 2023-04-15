import functools
import shutil
import subprocess
from typing import Optional, Type

from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
# Clients:
<bind address="{hostname}" port="{port}" type="clients">
{ssl_config}
<connect allow="*"
    resolvehostnames="no" # Faster
    recvq="40960" # Needs to be larger than a valid message with tags
    timeout="10"  # So tests don't hang too long
    localmax="1000"
    globalmax="1000"
    {password_field}>

<class
    name="ServerOperators"
    commands="WALLOPS GLOBOPS"
    privs="channels/auspex users/auspex channels/auspex servers/auspex"
    >
<type
    name="NetAdmin"
    classes="ServerOperators"
    >
<oper name="operuser"
      password="operpassword"
      host="*@*"
      type="NetAdmin"
      class="ServerOperators"
      >

<options casemapping="ascii">

# Disable 'NOTICE #chan :*** foo invited bar into the channel-
<security announceinvites="none">

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
<module name="banexception">
<module name="botmode">
<module name="cap">
<module name="inviteexception">
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

# HELP/HELPOP
<module name="alias">  # for the HELP alias
<module name="{help_module_name}">
<include file="examples/{help_module_name}.conf.example">

# Misc:
<log method="file" type="*" level="debug" target="/tmp/ircd-{port}.log">
<server name="My.Little.Server" description="test server" id="000" network="testnet">
"""

TEMPLATE_SSL_CONFIG = """
<module name="ssl_openssl">
<openssl certfile="{pem_path}" keyfile="{key_path}" dhfile="{dh_path}" hash="sha1">
"""


@functools.lru_cache()
def installed_version() -> int:
    output = subprocess.check_output(["inspircd", "--version"], universal_newlines=True)
    if output.startswith("InspIRCd-3"):
        return 3
    if output.startswith("InspIRCd-4"):
        return 4
    else:
        assert False, f"unexpected version: {output}"


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
        faketime: Optional[str] = None,
    ) -> None:
        assert self.proc is None
        self.port = port
        self.hostname = hostname
        self.create_config()
        (services_hostname, services_port) = self.get_hostname_and_port()

        password_field = 'password="{}"'.format(password) if password else ""

        if ssl:
            self.gen_ssl()
            ssl_config = TEMPLATE_SSL_CONFIG.format(
                key_path=self.key_path, pem_path=self.pem_path, dh_path=self.dh_path
            )
        else:
            ssl_config = ""

        if installed_version() == 3:
            help_module_name = "helpop"
        elif installed_version() == 4:
            help_module_name = "help"
        else:
            assert False, f"unexpected version: {installed_version()}"

        with self.open_file("server.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    hostname=hostname,
                    port=port,
                    services_hostname=services_hostname,
                    services_port=services_port,
                    password_field=password_field,
                    ssl_config=ssl_config,
                    help_module_name=help_module_name,
                )
            )
        assert self.directory

        if faketime and shutil.which("faketime"):
            faketime_cmd = ["faketime", "-f", faketime]
            self.faketime_enabled = True
        else:
            faketime_cmd = []

        self.proc = subprocess.Popen(
            [
                *faketime_cmd,
                "inspircd",
                "--nofork",
                "--config",
                self.directory / "server.conf",
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
