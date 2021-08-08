from typing import Type

from .base_hybrid import BaseHybridController

TEMPLATE_CONFIG = """
serverinfo {{
    name = "My.Little.Server";
    sid = "42X";
    description = "test server";
{ssl_config}
}};

general {{
    throttle_count = 100;  # We need to connect lots of clients quickly
    sasl_service = "SaslServ";
}};

class "server" {{
    ping_time = 5 minutes;
    connectfreq = 5 minutes;
}};

listen {{
    defer_accept = yes;

    host = "{hostname}";
    port = {port};
    port = {services_port};
}};

auth {{
    user = "*";
    flags = exceed_limit;
    {password_field}
}};

channel {{
    disable_local_channels = no;
    no_create_on_split = no;
    no_join_on_split = no;
    displayed_usercount = 0;
}};

connect "services.example.org" {{
    host = "localhost";  # Used to validate incoming connection
    port = 0;  # We don't need servers to connect to services
    send_password = "password";
    accept_password = "password";
    class = "server";
    flags = topicburst;
}};
service {{
    name = "services.example.org";
}};
"""


class CharybdisController(BaseHybridController):
    software_name = "Charybdis"
    binary_name = "charybdis"
    services_protocol = "charybdis"

    supported_sasl_mechanisms = {"PLAIN"}

    template_config = TEMPLATE_CONFIG


def get_irctest_controller_class() -> Type[CharybdisController]:
    return CharybdisController
