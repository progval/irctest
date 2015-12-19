class _BaseController:
    pass

class BaseClientController(_BaseController):
    def run(self, hostname, port, auth):
        raise NotImplementedError()

class BaseServerController(_BaseController):
    pass
