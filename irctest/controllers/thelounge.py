import json
import os
import subprocess
from typing import Optional, Type

from irctest import authentication, tls
from irctest.basecontrollers import (
    BaseClientController,
    DirectoryBasedController,
    NotImplementedByController,
)

TEMPLATE_CONFIG = """
"use strict";

module.exports = {config};
"""


class TheLoungeController(BaseClientController, DirectoryBasedController):
    software_name = "TheLounge"
    supported_sasl_mechanisms = {
        "PLAIN",
        "ECDSA-NIST256P-CHALLENGE",
        "SCRAM-SHA-256",
        "EXTERNAL",
    }
    supports_sts = True

    def create_config(self) -> None:
        super().create_config()
        with self.open_file("bot.conf"):
            pass
        with self.open_file("conf/users.conf"):
            pass

    def run(
        self,
        hostname: str,
        port: int,
        auth: Optional[authentication.Authentication],
        tls_config: Optional[tls.TlsConfig] = None,
    ) -> None:
        if tls_config is None:
            tls_config = tls.TlsConfig(enable=False, trusted_fingerprints=[])
        if tls_config and tls_config.trusted_fingerprints:
            raise NotImplementedByController("Trusted fingerprints.")
        if auth and any(
            mech.to_string().startswith(("SCRAM-", "ECDSA-"))
            for mech in auth.mechanisms
        ):
            raise NotImplementedByController("ecdsa")
        # Runs a client with the config given as arguments
        assert self.proc is None
        self.create_config()
        if auth:
            mechanisms = " ".join(mech.to_string() for mech in auth.mechanisms)
            if auth.ecdsa_key:
                with self.open_file("ecdsa_key.pem") as fd:
                    fd.write(auth.ecdsa_key)
        else:
            mechanisms = ""

        assert self.directory
        with self.open_file("config.js") as fd:
            fd.write(
                TEMPLATE_CONFIG.format(
                    config=json.dumps(
                        dict(
                            public=False,
                            host="unix:" + self.directory + "/sock",  # prevents binding
                        )
                    )
                )
            )
        with self.open_file("users/testuser.json") as fd:
            json.dump(
                dict(
                    networks=[
                        dict(
                            name="testnet",
                            host=hostname,
                            port=port,
                            tls=tls_config.enable if tls_config else "False",
                            sasl=mechanisms.lower(),
                            saslAccount=auth.username if auth else "",
                            saslPassword=auth.password if auth else "",
                        )
                    ]
                ),
                fd,
            )
        with self.open_file("users/testuser.json", "r") as fd:
            print("config", json.load(fd)["networks"][0]["saslPassword"])
        self.proc = subprocess.Popen(
            [os.environ.get("THELOUNGE_BIN", "thelounge"), "start"],
            env={**os.environ, "THELOUNGE_HOME": os.path.join(self.directory)},
        )


def get_irctest_controller_class() -> Type[TheLoungeController]:
    return TheLoungeController
