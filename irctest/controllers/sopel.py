import os
import tempfile
import subprocess

from irctest.basecontrollers import BaseClientController
from irctest.basecontrollers import NotImplementedByController

TEMPLATE_CONFIG = """
[core]
nick = Sopel
host = {hostname}
use_ssl = false
port = {port}
owner = me
channels = 
timeout = 5
auth_username = {username}
auth_password = {password}
{auth_method}
"""

class SopelController(BaseClientController):
    software_name = 'Sopel'
    supported_sasl_mechanisms = {
            'PLAIN',
            }
    def __init__(self):
        super().__init__()
        self.filename = next(tempfile._get_candidate_names()) + '.cfg'
        self.proc = None
    def kill(self):
        if self.proc:
            self.proc.kill()
        if self.filename:
            try:
                os.unlink(os.path.join(os.path.expanduser('~/.sopel/'),
                    self.filename))
            except OSError: # File does not exist
                pass

    def open_file(self, filename, mode='a'):
        return open(os.path.join(os.path.expanduser('~/.sopel/'), filename),
                mode)

    def create_config(self):
        with self.open_file(self.filename) as fd:
            pass

    def run(self, hostname, port, auth, tls_config):
        # Runs a client with the config given as arguments
        if tls_config is not None:
            raise NotImplementedByController(
                    'TLS configuration')
        assert self.proc is None
        self.create_config()
        with self.open_file(self.filename) as fd:
            fd.write(TEMPLATE_CONFIG.format(
                hostname=hostname,
                port=port,
                username=auth.username if auth else '',
                password=auth.password if auth else '',
                auth_method='auth_method = sasl' if auth else '',
                ))
        self.proc = subprocess.Popen(['sopel', '--quiet', '-c', self.filename])

def get_irctest_controller_class():
    return SopelController

