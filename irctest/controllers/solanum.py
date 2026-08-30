from typing import Type

from .charybdis import TEMPLATE_CONFIG, CharybdisController


class SolanumController(CharybdisController):
    software_name = "Solanum"
    binary_name = "solanum"

    template_config = (
        'loadmodule "extensions/tag_message_id";\n'
        'loadmodule "extensions/botmode";\n'
        'loadmodule "extensions/multiline";\n'
        "general {{ multiline_max_lines = 10; multiline_max_bytes = 2000; }}\n"
        'loadmodule "extensions/extb_account";\n' + TEMPLATE_CONFIG
    )


def get_irctest_controller_class() -> Type[SolanumController]:
    return SolanumController
