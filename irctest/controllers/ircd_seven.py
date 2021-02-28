from typing import Type

from .charybdis import CharybdisController


class IrcdSevenController(CharybdisController):
    software_name = "ircd-seven"
    binary_name = "ircd-seven"


def get_irctest_controller_class() -> Type[IrcdSevenController]:
    return IrcdSevenController
