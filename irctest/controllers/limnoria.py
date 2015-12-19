import os
import subprocess

from irctest import authentication
from irctest.basecontrollers import BaseClientController, DirectoryBasedController

TEMPLATE_CONFIG = """
supybot.directories.conf: {directory}/conf
supybot.directories.data: {directory}/data
supybot.log.stdout.level: {loglevel}
supybot.networks: testnet
supybot.networks.testnet.servers: {hostname}:{port}
supybot.networks.testnet.sasl.username: {username}
supybot.networks.testnet.sasl.password: {password}
supybot.networks.testnet.sasl.mechanisms: {mechanisms}
"""

class LimnoriaController(BaseClientController, DirectoryBasedController):
    def create_config(self):
        super().create_config()
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
                directory=self.directory,
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
