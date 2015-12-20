import os
import time
import shutil
import tempfile
import subprocess

from irctest import authentication
from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
clients:
  # ping_frequency - client ping frequency
  ping_frequency:
    minutes: 1000

  # ping_timeout - ping timeout length
  ping_timeout:
    seconds: 10
data:
  format: json
  filename: {directory}/data.json
  save_frequency:
    minutes: 5
extensions:
- mammon.ext.rfc1459.42
- mammon.ext.rfc1459.ident
- mammon.ext.ircv3.account_notify
- mammon.ext.ircv3.server_time
- mammon.ext.ircv3.echo_message
- mammon.ext.ircv3.register
- mammon.ext.ircv3.sasl
- mammon.ext.misc.nopost
metadata:
  restricted_keys: 
monitor:
  limit: 20
motd:
  - "Hi"
limits:
  foo: bar
listeners:
- {{"host": "{hostname}", "port": {port}, "ssl": false}}
logs:
  {{
  }}
register:
  foo: bar
roles:
  "placeholder":
    title: "Just a placeholder"
server:
  name: MyLittleServer
  network: MyLittleNetwork
  recvq_len: 20
"""

class InspircdController(BaseServerController, DirectoryBasedController):
    def create_config(self):
        super().create_config()
        with self.open_file('server.conf'):
            pass

    def kill_proc(self):
        # Mammon does not seem to handle SIGTERM very well
        self.proc.kill()

    def run(self, hostname, port):
        assert self.proc is None
        self.create_config()
        with self.open_file('server.yml') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                directory=self.directory,
                hostname=hostname,
                port=port,
                ))
        self.proc = subprocess.Popen(['python3', '-m', 'mammon', '--nofork', #'--debug',
            '--config', os.path.join(self.directory, 'server.yml')])
        time.sleep(0.5) # FIXME: do better than this to wait for Mammon to start

def get_irctest_controller_class():
    return InspircdController


