class _BaseController:
    pass

class BaseClientController(_BaseController):
    def run(self, hostname, port, authentication):
        raise NotImplementedError()

class BaseServerController(_BaseController):
    pass
