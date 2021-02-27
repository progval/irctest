from .charybdis import CharybdisController


class SolanumController(CharybdisController):
    software_name = "Solanum"
    binary_name = "solanum"


def get_irctest_controller_class():
    return SolanumController
