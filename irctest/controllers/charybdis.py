import os
import time
import shutil
import tempfile
import subprocess

from irctest import client_mock
from irctest import authentication
from irctest.basecontrollers import NotImplementedByController
from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
serverinfo {{
    name = "My.Little.Server";
    sid = "42X";
    description = "test server";
{ssl_config}
}};
listen {{
    defer_accept = yes;

    host = "{hostname}";
    port = {port};
}};
auth {{
    user = "*";
    flags = exceed_limit;
    {password_field}
}};
channel {{
    disable_local_channels = no;
    no_create_on_split = no;
    no_join_on_split = no;
    displayed_usercount = 0;
}};
"""

TEMPLATE_SSL_CONFIG = """
    ssl_private_key = "{key_path}";
    ssl_cert = "{pem_path}";
    ssl_dh_params = "{dh_path}";
"""


class CharybdisController(BaseServerController, DirectoryBasedController):
    software_name = 'Charybdis'
    supported_sasl_mechanisms = set()
    def create_config(self):
        super().create_config()
        with self.open_file('server.conf'):
            pass

    def run(self, hostname, port, password=None, ssl=False,
            valid_metadata_keys=None, invalid_metadata_keys=None):
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                    'Defining valid and invalid METADATA keys.')
        assert self.proc is None
        self.create_config()
        self.port = port
        password_field = 'password = "{}";'.format(password) if password else ''
        if ssl:
            self.gen_ssl()
            ssl_config = TEMPLATE_SSL_CONFIG.format(
                    key_path=self.key_path,
                    pem_path=self.pem_path,
                    dh_path=self.dh_path,
                    )
        else:
            ssl_config = ''
        with self.open_file('server.conf') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                hostname=hostname,
                port=port,
                password_field=password_field,
                ssl_config=ssl_config,
                ))
        self.proc = subprocess.Popen(['charybdis', '-foreground',
            '-configfile', os.path.join(self.directory, 'server.conf'),
            '-pidfile', os.path.join(self.directory, 'server.pid'),
            ],
            stderr=subprocess.DEVNULL
            )


def get_irctest_controller_class():
    return CharybdisController
