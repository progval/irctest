import os
import subprocess

from irctest.basecontrollers import (
    BaseServerController,
    DirectoryBasedController,
    NotImplementedByController,
)

TEMPLATE_CONFIG = """
<bind address="{hostname}" port="{port}" type="clients">
{ssl_config}
<module name="cap">
<module name="ircv3">
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
<connect allow="*"
    resolvehostnames="no" # Faster
    recvq="40960" # Needs to be larger than a valid message with tags
    {password_field}>
<log method="file" type="*" level="debug" target="/tmp/ircd-{port}.log">
"""

TEMPLATE_SSL_CONFIG = """
<module name="ssl_openssl">
<openssl certfile="{pem_path}" keyfile="{key_path}" dhfile="{dh_path}" hash="sha1">
"""


class InspircdController(BaseServerController, DirectoryBasedController):
    software_name = "InspIRCd"
    supported_sasl_mechanisms = set()
    supported_capabilities = set()  # Not exhaustive

    def create_config(self):
        super().create_config()
        with self.open_file("server.conf"):
            pass

    def run(
        self,
        hostname,
        port,
        password=None,
        ssl=False,
        restricted_metadata_keys=None,
        valid_metadata_keys=None,
        invalid_metadata_keys=None,
    ):
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                "Defining valid and invalid METADATA keys."
            )
        assert self.proc is None
        self.port = port
        self.create_config()
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
                    password_field=password_field,
                    ssl_config=ssl_config,
                )
            )
        self.proc = subprocess.Popen(
            [
                "inspircd",
                "--nofork",
                "--config",
                os.path.join(self.directory, "server.conf"),
            ],
            stdout=subprocess.DEVNULL,
        )


def get_irctest_controller_class():
    return InspircdController
