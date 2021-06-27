import os
import subprocess
import time
from typing import IO, Any, List, Optional

try:
    from typing import Protocol
except ImportError:
    # Python < 3.8
    from typing_extensions import Protocol  # type: ignore

import irctest
from irctest.basecontrollers import DirectoryBasedController
import irctest.cases
from irctest.client_mock import ClientMock
from irctest.irc_utils.message_parser import Message
import irctest.runner

TEMPLATE_CONFIG = """
loadmodule "modules/protocol/inspircd";
loadmodule "modules/backend/opensex";
loadmodule "modules/crypto/pbkdf2";

loadmodule "modules/nickserv/main";
loadmodule "modules/nickserv/cert";
loadmodule "modules/nickserv/register";
loadmodule "modules/nickserv/verify";

loadmodule "modules/saslserv/authcookie";
#loadmodule "modules/saslserv/ecdh-x25519-challenge";
loadmodule "modules/saslserv/ecdsa-nist256p-challenge";
loadmodule "modules/saslserv/external";
loadmodule "modules/saslserv/plain";
#loadmodule "modules/saslserv/scram";

serverinfo {{
    name = "services.example.org";
    desc = "Atheme IRC Services";
    numeric = "00A";
    netname = "testnet";
    adminname = "no admin";
    adminemail = "no-admin@example.org";
    registeremail = "registration@example.org";
    auth = none;  // Disable email check
}};

general {{
    commit_interval = 5;
}};

uplink "irc.example.com" {{
    host = "{server_hostname}";
    port = {server_port};
    send_password = "password";
    receive_password = "password";
}};

saslserv {{
    nick = "SaslServ";
}};
"""


class _Controller(Protocol):
    # Magic class to make mypy accept AthemeServices as a mixin without actually
    # inheriting.
    directory: Optional[str]
    hostname: str
    port: int
    services_proc: subprocess.Popen

    def wait_for_port(self) -> None:
        ...

    def open_file(self, name: str, mode: str = "a") -> IO:
        ...

    def getNickServResponse(self, client: Any) -> List[Message]:
        ...


class AthemeServices(DirectoryBasedController):
    """Mixin for server controllers that rely on Atheme"""

    def __init__(self, *args, **kwargs):  # type: ignore
        super().__init__(*args, **kwargs)
        self.services_proc = None

    def run_services(self: _Controller, server_hostname: str, server_port: int) -> None:
        with self.open_file("services.conf") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    server_hostname=server_hostname,
                    server_port=server_port,
                )
            )

        assert self.directory
        self.services_proc = subprocess.Popen(
            [
                "atheme-services",
                "-n",  # don't fork
                "-c",
                os.path.join(self.directory, "services.conf"),
                "-l",
                f"/tmp/services-{server_port}.log",
                "-p",
                os.path.join(self.directory, "services.pid"),
                "-D",
                self.directory,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def kill_proc(self) -> None:
        super().kill_proc()
        if self.services_proc is not None:
            self.services_proc.kill()
            self.services_proc = None

    def wait_for_services(self: _Controller) -> None:
        self.wait_for_port()

        c = ClientMock(name="chkNS", show_io=True)
        c.connect(self.hostname, self.port)
        c.sendLine("NICK chkNS")
        c.sendLine("USER chk chk chk chk")
        c.getMessages(synchronize=False)

        msgs: List[Message] = []
        while not msgs:
            c.sendLine("PRIVMSG NickServ :HELP")
            msgs = self.getNickServResponse(c)
        if msgs[0].command == "401":
            # NickServ not available yet
            pass
        elif msgs[0].command == "NOTICE":
            # NickServ is available
            assert "nickserv" in (msgs[0].prefix or "").lower(), msgs
        else:
            assert False, f"unexpected reply from NickServ: {msgs[0]}"

        c.sendLine("QUIT")
        c.getMessages()
        c.disconnect()

    def getNickServResponse(self, client: Any) -> List[Message]:
        """Wrapper aroung getMessages() that waits longer, because NickServ
        is queried asynchronously."""
        msgs: List[Message] = []
        while not msgs:
            time.sleep(0.05)
            msgs = client.getMessages()
        return msgs

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        if not case.run_services:
            raise ValueError(
                "Attempted to register a nick, but `run_services` it not True."
            )
        assert password
        if len(password.encode()) > 288:
            # It's hardcoded at compile-time :(
            # https://github.com/atheme/atheme/blob/4fa0e03bd3ce2cb6041a339f308616580c5aac29/include/atheme/constants.h#L51
            raise irctest.runner.NotImplementedByController("Passwords over 288 bytes")
        client = case.addClient(show_io=True)
        case.sendLine(client, "NICK " + username)
        case.sendLine(client, "USER r e g :user")
        while case.getRegistrationMessage(client).command != "001":
            pass
        case.getMessages(client)
        case.sendLine(client, f"PRIVMSG NickServ :REGISTER {password} foo@example.org")
        msgs = self.getNickServResponse(case.clients[client])
        assert "900" in {msg.command for msg in msgs}, msgs
        case.sendLine(client, "QUIT")
        case.assertDisconnected(client)
