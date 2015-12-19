import os
import tempfile
import subprocess

from irctest.basecontrollers import BaseClientController

TEMPLATE_CONFIG = """
[core]
nick = Sopel
host = {hostname}
use_ssl = false
port = {port}
owner = me
channels = 
"""

class SopelController(BaseClientController):
    def __init__(self):
        super().__init__()
        self.filename = next(tempfile._get_candidate_names())
        self.proc = None
    def __del__(self):
        if self.proc:
            self.proc.kill()
        if self.filename:
            try:
                os.unlink(os.path.join(os.path.expanduser('~/.sopel/'),
                    self.filename))
            except OSError: # File does not exist
                pass

    def open_file(self, filename):
        return open(os.path.join(os.path.expanduser('~/.sopel/'), filename),
                'a')

    def create_config(self):
        self.directory = tempfile.TemporaryDirectory()
        with self.open_file(self.filename) as fd:
            pass

    def run(self, hostname, port, authentication):
        # Runs a client with the config given as arguments
        self.create_config()
        with self.open_file(self.filename) as fd:
            fd.write(TEMPLATE_CONFIG.format(
                hostname=hostname,
                port=port,
                ))
        self.proc = subprocess.Popen(['sopel', '-c', self.filename])

def get_irctest_controller_class():
    return SopelController

