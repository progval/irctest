import os
import shutil
import tempfile
import subprocess

from irctest import authentication
from irctest.basecontrollers import BaseClientController

TEMPLATE_CONFIG = """
supybot.log.stdout.level: {loglevel}
supybot.networks: testnet
supybot.networks.testnet.servers: {hostname}:{port}
supybot.networks.testnet.sasl.username: {username}
supybot.networks.testnet.sasl.password: {password}
supybot.networks.testnet.sasl.mechanisms: {mechanisms}
"""

class LimnoriaController(BaseClientController):
    def __init__(self):
        super().__init__()
        self.directory = None
        self.proc = None
    def kill(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None
        if self.directory:
            shutil.rmtree(self.directory)
    def open_file(self, name, mode='a'):
        assert self.directory
        if os.sep in name:
            dir_ = os.path.join(self.directory, os.path.dirname(name))
            if not os.path.isdir(dir_):
                os.makedirs(dir_)
            assert os.path.isdir(dir_)
        return open(os.path.join(self.directory, name), mode)

    def create_config(self):
        self.directory = tempfile.mkdtemp()
        with self.open_file('bot.conf'):
            pass
        with self.open_file('conf/users.conf'):
            pass

    def run(self, hostname, port, auth):
        # Runs a client with the config given as arguments
        assert self.proc is None
        self.create_config()
        if auth:
            mechanisms = ' '.join(map(authentication.Mechanisms.as_string,
                auth.mechanisms))
        else:
            mechanisms = ''
        with self.open_file('bot.conf') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                loglevel='CRITICAL',
                hostname=hostname,
                port=port,
                username=auth.username if auth else '',
                password=auth.password if auth else '',
                mechanisms=mechanisms.lower(),
                ))
        self.proc = subprocess.Popen(['supybot',
            os.path.join(self.directory, 'bot.conf')])

def get_irctest_controller_class():
    return LimnoriaController
