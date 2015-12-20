import os
import time
import subprocess

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
  enabled_callbacks:
  - none
  verify_timeout:
    days: 1
roles:
  "placeholder":
    title: "Just a placeholder"
server:
  name: MyLittleServer
  network: MyLittleNetwork
  recvq_len: 20
"""

class MammonController(BaseServerController, DirectoryBasedController):
    supported_sasl_mechanisms = {
            'PLAIN', 'ECDSA-NIST256P-CHALLENGE',
            }
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
        self.proc = subprocess.Popen(['mammond', '--nofork', #'--debug',
            '--config', os.path.join(self.directory, 'server.yml')])
        self.wait_for_port(self.proc, port)

    def registerUser(self, case, username, password=None):
        # XXX: Move this somewhere else when
        # https://github.com/ircv3/ircv3-specifications/pull/152 becomes
        # part of the specification
        client = case.addClient()
        case.sendLine(client, 'CAP LS 302')
        case.sendLine(client, 'NICK registration_user')
        case.sendLine(client, 'USER r e g :user')
        case.sendLine(client, 'CAP END')
        list(case.getLines(client))
        case.sendLine(client, 'REG CREATE {} passphrase {}'.format(
            username, password))
        msg = case.getMessage(client)
        assert msg.command == '920'
        list(case.getLines(client))
        case.removeClient(client)

def get_irctest_controller_class():
    return MammonController
