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
}};
"""
class CharybdisController(BaseServerController, DirectoryBasedController):
    software_name = 'Charybdis'
    supported_sasl_mechanisms = set()
    def create_config(self):
        super().create_config()
        with self.open_file('server.conf'):
            pass

    def run(self, hostname, port, password=None,
            valid_metadata_keys=None, invalid_metadata_keys=None):
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                    'Defining valid and invalid METADATA keys.')
        assert self.proc is None
        self.create_config()
        password_field = 'password = "{}";'.format(password) if password else ''
        with self.open_file('server.conf') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                hostname=hostname,
                port=port,
                password_field=password_field
                ))
        self.proc = subprocess.Popen(['ircd', '-foreground',
            '-configfile', os.path.join(self.directory, 'server.conf'),
            '-pidfile', os.path.join(self.directory, 'server.pid'),
            ],
            stderr=subprocess.DEVNULL
            )
        self.wait_for_port(self.proc, port)


def get_irctest_controller_class():
    return CharybdisController
