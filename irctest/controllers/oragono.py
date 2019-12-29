import copy
import json
import os
import subprocess

from irctest.basecontrollers import NotImplementedByController
from irctest.basecontrollers import BaseServerController, DirectoryBasedController

BASE_CONFIG = {
    "network": {
        "name": "OragonoTest",
    },

    "server": {
        "name": "oragono.test",
        "listeners": {},
        "max-sendq": "16k",
        "connection-limits": {
            "enabled": True,
            "cidr-len-ipv4": 32,
            "cidr-len-ipv6": 64,
            "ips-per-subnet": 1,
            "exempted": ["localhost"],
        },
        "connection-throttling": {
            "enabled": True,
            "cidr-len-ipv4": 32,
            "cidr-len-ipv6": 64,
            "ips-per-subnet": 16,
            "duration": "10m",
            "max-connections": 1,
            "ban-duration": "10m",
            "ban-message": "Try again later",
            "exempted": ["localhost"],
        },
    },

    'accounts': {
	'authentication-enabled': True,
	'bouncer': {'allowed-by-default': False, 'enabled': True},
	'registration': {
	    'bcrypt-cost': 4,
	    'enabled': True,
	    'enabled-callbacks': ['none'],
	    'verify-timeout': '120h',
	},
    },

   "channels": {
       "registration": {"enabled": True,},
   },

   "datastore": {
       "path": None,
   },

   'limits': {
       'awaylen': 200,
       'chan-list-modes': 60,
       'channellen': 64,
       'kicklen': 390,
       'linelen': {'rest': 2048,},
       'monitor-entries': 100,
       'nicklen': 32,
       'topiclen': 390,
       'whowas-entries': 100,
       'multiline': {'max-bytes': 4096, 'max-lines': 32,},
   },

   "history": {
       "enabled": True,
       "channel-length": 128,
       "client-length": 128,
   },
}

def hash_password(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    # simulate entry of password and confirmation:
    input_ = password + b'\n' + password + b'\n'
    p = subprocess.Popen(['oragono', 'genpasswd'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out, _ = p.communicate(input_)
    return out.decode('utf-8')

class OragonoController(BaseServerController, DirectoryBasedController):
    software_name = 'Oragono'
    supported_sasl_mechanisms = {
            'PLAIN',
    }

    def kill_proc(self):
        self.proc.kill()

    def run(self, hostname, port, password=None, ssl=False,
            restricted_metadata_keys=None,
            valid_metadata_keys=None, invalid_metadata_keys=None):
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                    'Defining valid and invalid METADATA keys.')

        self.create_config()
        config = copy.deepcopy(BASE_CONFIG)

        self.port = port
        bind_address = ":%s" % (port,)
        listener_conf = None # plaintext
        if ssl:
            self.key_path = os.path.join(self.directory, 'ssl.key')
            self.pem_path = os.path.join(self.directory, 'ssl.pem')
            listener_conf = {"tls": {"cert": self.pem_path, "key": self.key_path},}
        config['server']['listeners'][bind_address] = listener_conf

        config['datastore']['path'] = os.path.join(self.directory, 'ircd.db')

        if password is not None:
            config['server']['password'] = hash_password(password)

        assert self.proc is None

        with self.open_file('server.yml', 'w') as fd:
            json.dump(config, fd)
        subprocess.call(['oragono', 'initdb',
            '--conf', os.path.join(self.directory, 'server.yml'), '--quiet'])
        subprocess.call(['oragono', 'mkcerts',
            '--conf', os.path.join(self.directory, 'server.yml'), '--quiet'])
        self.proc = subprocess.Popen(['oragono', 'run',
            '--conf', os.path.join(self.directory, 'server.yml'), '--quiet'])

    def registerUser(self, case, username, password=None):
        # XXX: Move this somewhere else when
        # https://github.com/ircv3/ircv3-specifications/pull/152 becomes
        # part of the specification
        client = case.addClient(show_io=False)
        case.sendLine(client, 'CAP LS 302')
        case.sendLine(client, 'NICK ' + username)
        case.sendLine(client, 'USER r e g :user')
        case.sendLine(client, 'CAP END')
        while case.getRegistrationMessage(client).command != '001':
            pass
        case.getMessages(client)
        case.sendLine(client, 'NS REGISTER ' + password)
        msg = case.getMessage(client)
        assert msg.params == [username, 'Account created']
        case.sendLine(client, 'QUIT')
        case.assertDisconnected(client)

def get_irctest_controller_class():
    return OragonoController
