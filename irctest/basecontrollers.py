import os
import shutil
import socket
import tempfile
import subprocess

class _BaseController:
    pass

class DirectoryBasedController(_BaseController):
    def __init__(self):
        super().__init__()
        self.directory = None
        self.proc = None

    def kill_proc(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None
    def kill(self):
        if self.proc:
            self.kill_proc()
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

class BaseClientController(_BaseController):
    def run(self, hostname, port, auth):
        raise NotImplementedError()

class BaseServerController(_BaseController):
    pass
