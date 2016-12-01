import subprocess

from irctest.basecontrollers import BaseClientController, NotImplementedByController

class GircController(BaseClientController):
    software_name = 'gIRC'

    def __init__(self):
        super().__init__()
        self.directory = None
        self.proc = None
        self.supported_sasl_mechanisms = ['PLAIN']

    def kill(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def __del__(self):
        if self.proc:
            self.proc.kill()
        if self.directory:
            self.directory.cleanup()

    def run(self, hostname, port, auth, tls_config):
        if tls_config:
            print(tls_config)
            raise NotImplementedByController('TLS options')
        args = ['--host', hostname, '--port', str(port), '--quiet']

        if auth and auth.username and auth.password:
            args += ['--sasl-name', auth.username]
            args += ['--sasl-pass', auth.password]
            args += ['--sasl-fail-is-ok']

        # Runs a client with the config given as arguments
        self.proc = subprocess.Popen(['girc_test', 'connect'] + args)

def get_irctest_controller_class():
    return GircController
