from typing import Set, Type

from .base_hybrid import BaseHybridController

TEMPLATE_CONFIG = """
serverinfo {{
    name = "My.Little.Server";
    sid = "42X";
    description = "test server";

    # Hybrid defaults to 9
    max_nick_length = 20;
{ssl_config}
}};

general {{
    throttle_count = 100;  # We need to connect lots of clients quickly
    sasl_service = "SaslServ";

    # Allow connections quickly
    throttle_num = 100;

    # Allow PART/QUIT reasons quickly
    anti_spam_exit_message_time = 0;

    # Allow all commands quickly
    pace_wait_simple = 0;
    pace_wait = 0;
}};

listen {{
    defer_accept = yes;

    host = "{hostname}";
    port = {port};

    flags = server;
    port = {services_port};
}};

class {{
    name = "server";
    ping_time = 5 minutes;
    connectfreq = 5 minutes;
}};
connect {{
    name = "services.example.org";
    host = "localhost";  # Used to validate incoming connection
    port = 0;  # We don't need servers to connect to services
    send_password = "password";
    accept_password = "password";
    class = "server";
}};
service {{
    name = "services.example.org";
}};

auth {{
    user = "*";
    flags = exceed_limit;
    {password_field}
}};

operator {{
    name = "operuser";
    user = "*@*";
    password = "operpassword";
    encrypted = no;
    umodes = locops, servnotice, wallop;
    flags = admin, connect, connect:remote, die, globops, kill, kill:remote,
            kline, module, rehash, restart, set, unkline, unxline, xline;
}};
"""


class Plexus4Controller(BaseHybridController):
    software_name = "Hybrid"
    binary_name = "ircd"
    services_protocol = "plexus"

    supported_sasl_mechanisms: Set[str] = set()

    template_config = TEMPLATE_CONFIG


def get_irctest_controller_class() -> Type[Plexus4Controller]:
    return Plexus4Controller
