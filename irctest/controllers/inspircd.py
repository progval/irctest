import os
import time
import shutil
import tempfile
import subprocess

from irctest import authentication
from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
<bind address="{hostname}" port="{port}" type="clients">
<module name="cap">
<module name="ircv3">
<module name="ircv3_capnotify">
<module name="namesx"> # For multi-prefix
<connect allow="*"
    resolvehostnames="no" # Faster
    {password_field}>
<log method="file" type="*" level="debug" target="/tmp/ircd-{port}.log">
"""

class InspircdController(BaseServerController, DirectoryBasedController):
    supported_sasl_mechanisms = set()
    def create_config(self):
        super().create_config()
        with self.open_file('server.conf'):
            pass

    def run(self, hostname, port, password=None):
        assert self.proc is None
        self.create_config()
        password_field = 'password="{}"'.format(password) if password else ''
        with self.open_file('server.conf') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                hostname=hostname,
                port=port,
                password_field=password_field
                ))
        self.proc = subprocess.Popen(['inspircd', '--nofork', '--config',
            os.path.join(self.directory, 'server.conf')],
            stdout=subprocess.DEVNULL
            )
        self.wait_for_port(self.proc, port)

def get_irctest_controller_class():
    return InspircdController

