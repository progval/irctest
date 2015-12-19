import os
import tempfile
import subprocess

from irctest.basecontrollers import BaseClientController

TEMPLATE_CONFIG = """
supybot.networks: testnet
supybot.networks.testnet.servers: {hostname}:{port}
"""

class LimnoriaController(BaseClientController):
    def __init__(self):
        super().__init__()
        self.directory = None
        self.proc = None
    def __del__(self):
        if self.proc:
            self.proc.kill()
        if self.directory:
            self.directory.cleanup()
    def open_file(self, name):
        assert self.directory
        return open(os.path.join(self.directory.name, name), 'a')

    def create_config(self):
        self.directory = tempfile.TemporaryDirectory()
        with self.open_file('bot.conf'):
            pass

    def run(self, hostname, port, authentication):
        # Runs a client with the config given as arguments
        self.create_config()
        with self.open_file('bot.conf') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                hostname=hostname,
                port=port,
                ))
        self.proc = subprocess.Popen(['supybot',
            os.path.join(self.directory.name, 'bot.conf')])

def get_irctest_controller_class():
    return LimnoriaController
