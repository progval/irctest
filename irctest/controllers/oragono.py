import os
import time
import subprocess

from irctest.basecontrollers import NotImplementedByController
from irctest.basecontrollers import BaseServerController, DirectoryBasedController

TEMPLATE_CONFIG = """
network:
    name: OragonoTest

server:
    name: oragono.test
    listen:
        - "{hostname}:{port}"
    {tls}

    check-ident: false

    max-sendq: 16k

    connection-limits:
        cidr-len-ipv4: 24
        cidr-len-ipv6: 120
        ips-per-subnet: 16

        exempted:
            - "127.0.0.1/8"
            - "::1/128"

    connection-throttling:
        enabled: true
        cidr-len-ipv4: 32
        cidr-len-ipv6: 128
        duration: 10m
        max-connections: 12
        ban-duration: 10m
        ban-message: You have attempted to connect too many times within a short duration. Wait a while, and you will be able to connect.

        exempted:
            - "127.0.0.1/8"
            - "::1/128"

accounts:
    registration:
        enabled: true
        verify-timeout: "120h"
        enabled-callbacks:
            - none # no verification needed, will instantly register successfully
        allow-multiple-per-connection: true

    authentication-enabled: true

channels:
    registration:
        enabled: true

datastore:
    path: {directory}/ircd.db

limits:
    nicklen: 32
    channellen: 64
    awaylen: 200
    kicklen: 390
    topiclen: 390
    monitor-entries: 100
    whowas-entries: 100
    chan-list-modes: 60
    linelen:
        tags: 2048
        rest: 2048
"""

class OragonoController(BaseServerController, DirectoryBasedController):
    software_name = 'Oragono'
    supported_sasl_mechanisms = {
            'PLAIN',
    }
    def create_config(self):
        super().create_config()
        with self.open_file('ircd.yaml'):
            pass

    def kill_proc(self):
        self.proc.kill()

    def run(self, hostname, port, password=None, ssl=False,
            restricted_metadata_keys=None,
            valid_metadata_keys=None, invalid_metadata_keys=None):
        if valid_metadata_keys or invalid_metadata_keys:
            raise NotImplementedByController(
                    'Defining valid and invalid METADATA keys.')
        if password is not None:
            #TODO(dan): fix dis
            raise NotImplementedByController('PASS command')
        self.create_config()
        tls_config = ""
        if ssl:
            self.key_path = os.path.join(self.directory, 'ssl.key')
            self.pem_path = os.path.join(self.directory, 'ssl.pem')
            tls_config = 'tls-listeners:\n        ":{port}":\n            key: {key}\n            cert: {pem}'.format(
                port=port,
                key=self.key_path,
                pem=self.pem_path,
            )
        assert self.proc is None
        self.port = port
        with self.open_file('server.yml') as fd:
            fd.write(TEMPLATE_CONFIG.format(
                directory=self.directory,
                hostname=hostname,
                port=port,
                tls=tls_config,
                ))
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
        case.sendLine(client, 'NICK registration_user')
        case.sendLine(client, 'USER r e g :user')
        case.sendLine(client, 'CAP END')
        while case.getRegistrationMessage(client).command != '001':
            pass
        list(case.getMessages(client))
        case.sendLine(client, 'ACC REGISTER {} passphrase {}'.format(
            username, password))
        msg = case.getMessage(client)
        assert msg.command == '920', msg
        list(case.getMessages(client))
        case.removeClient(client)

def get_irctest_controller_class():
    return OragonoController
