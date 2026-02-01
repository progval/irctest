from typing import Type

from .charybdis import TEMPLATE_CONFIG, CharybdisController


class SolanumController(CharybdisController):
    software_name = "Solanum"
    binary_name = "solanum"

    template_config = 'loadmodule "extensions/tag_message_id";\n' + TEMPLATE_CONFIG


def get_irctest_controller_class() -> Type[SolanumController]:
    return SolanumController
