from typing import Type

from .ircu2 import Ircu2Controller


class NefariousController(Ircu2Controller):
    software_name = "Nefarious"


def get_irctest_controller_class() -> Type[NefariousController]:
    return NefariousController
