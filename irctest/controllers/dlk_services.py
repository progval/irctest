import os
from pathlib import Path
import secrets
import subprocess
from typing import Optional, Type

import irctest
from irctest.basecontrollers import BaseServicesController, DirectoryBasedController
import irctest.cases
import irctest.runner

TEMPLATE_DLK_CONFIG = """\
info {{
    SID "00A";
    network-name "testnetwork";
    services-name "services.example.org";
    admin-email "admin@example.org";
}}

link {{
    hostname "{server_hostname}";
    port "{server_port}";
    password "password";
}}

log {{
    debug "yes";
}}

sql {{
    port "3306";
    username "pifpaf";
    password "pifpaf";
    database "pifpaf";
    sockfile "{mysql_socket}";
    prefix "{dlk_prefix}";
}}

wordpress {{
    prefix "{wp_prefix}";
}}

"""

TEMPLATE_DLK_WP_CONFIG = """
<?php

global $wpconfig;
$wpconfig = [

    "dbprefix" => "{wp_prefix}",


    "default_avatar" => "https://valware.uk/wp-content/plugins/ultimate-member/assets/img/default_avatar.jpg",
    "forumschan" => "#DLK-Support",

];
"""

TEMPLATE_WP_CONFIG = """
define( 'DB_NAME', 'pifpaf' );
define( 'DB_USER', 'pifpaf' );
define( 'DB_PASSWORD', 'pifpaf' );
define( 'DB_HOST', 'localhost:{mysql_socket}' );
define( 'DB_CHARSET', 'utf8' );
define( 'DB_COLLATE', '' );

define( 'AUTH_KEY',         'put your unique phrase here' );
define( 'SECURE_AUTH_KEY',  'put your unique phrase here' );
define( 'LOGGED_IN_KEY',    'put your unique phrase here' );
define( 'NONCE_KEY',        'put your unique phrase here' );
define( 'AUTH_SALT',        'put your unique phrase here' );
define( 'SECURE_AUTH_SALT', 'put your unique phrase here' );
define( 'LOGGED_IN_SALT',   'put your unique phrase here' );
define( 'NONCE_SALT',       'put your unique phrase here' );

$table_prefix = '{wp_prefix}';

define( 'WP_DEBUG', false );

if (!defined('ABSPATH')) {{
    define( 'ABSPATH', '{wp_path}' );
}}

/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */


/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
"""


class DlkController(BaseServicesController, DirectoryBasedController):
    """Mixin for server controllers that rely on DLK"""

    software_name = "Dlk-Services"

    def run_sql(self, sql: str) -> None:
        mysql_socket = os.environ["PIFPAF_MYSQL_SOCKET"]
        subprocess.run(
            ["mysql", "-S", mysql_socket, "pifpaf"],
            input=sql.encode(),
            check=True,
        )

    def run(self, protocol: str, server_hostname: str, server_port: int) -> None:
        self.create_config()

        if protocol == "unreal4":
            protocol = "unreal5"
        assert protocol in ("unreal5",), protocol

        mysql_socket = os.environ["PIFPAF_MYSQL_SOCKET"]

        assert self.directory

        try:
            self.wp_cli_path = Path(os.environ["IRCTEST_WP_CLI_PATH"])
            if not self.wp_cli_path.is_file():
                raise KeyError()
        except KeyError:
            raise RuntimeError(
                "$IRCTEST_WP_CLI_PATH must be set to a WP-CLI executable (eg. "
                "downloaded from <https://raw.githubusercontent.com/wp-cli/builds/"
                "gh-pages/phar/wp-cli.phar>)"
            ) from None

        try:
            self.dlk_path = Path(os.environ["IRCTEST_DLK_PATH"])
            if not self.dlk_path.is_dir():
                raise KeyError()
        except KeyError:
            raise RuntimeError("$IRCTEST_DLK_PATH is not set") from None
        self.dlk_path = self.dlk_path.resolve()

        # Unpack a fresh Wordpress install in the temporary directory.
        # In theory we could have a common Wordpress install and only wp-config.php
        # in the temporary directory; but wp-cli assumes wp-config.php must be
        # in a Wordpress directory, and fails in various places if it isn't.
        # Rather than symlinking everything to make it work, let's just copy
        # the whole code, it's not that big.
        try:
            wp_zip_path = Path(os.environ["IRCTEST_WP_ZIP_PATH"])
            if not wp_zip_path.is_file():
                raise KeyError()
        except KeyError:
            raise RuntimeError(
                "$IRCTEST_WP_ZIP_PATH must be set to a Wordpress source zipball "
                "(eg. downloaded from <https://wordpress.org/latest.zip>)"
            ) from None
        subprocess.run(
            ["unzip", wp_zip_path, "-d", self.directory], stdout=subprocess.DEVNULL
        )
        self.wp_path = self.directory / "wordpress"

        rand_hex = secrets.token_hex(6)
        self.wp_prefix = f"wp{rand_hex}_"
        self.dlk_prefix = f"dlk{rand_hex}_"
        template_vars = dict(
            protocol=protocol,
            server_hostname=server_hostname,
            server_port=server_port,
            mysql_socket=mysql_socket,
            wp_path=self.wp_path,
            wp_prefix=self.wp_prefix,
            dlk_prefix=self.dlk_prefix,
        )

        # Configure Wordpress
        wp_config_path = self.directory / "wp-config.php"
        with open(wp_config_path, "w") as fd:
            fd.write(TEMPLATE_WP_CONFIG.format(**template_vars))

        subprocess.run(
            [
                "php",
                self.wp_cli_path,
                "core",
                "install",
                "--url=http://localhost/",
                "--title=irctest site",
                "--admin_user=adminuser",
                "--admin_email=adminuser@example.org",
                f"--path={self.wp_path}",
            ],
            check=True,
        )

        # Configure Dlk
        dlk_log_dir = self.directory / "logs"
        dlk_conf_dir = self.directory / "conf"
        dlk_conf_path = dlk_conf_dir / "dalek.conf"
        os.mkdir(dlk_conf_dir)
        with open(dlk_conf_path, "w") as fd:
            fd.write(TEMPLATE_DLK_CONFIG.format(**template_vars))
        dlk_wp_config_path = dlk_conf_dir / "wordpress.conf"
        with open(dlk_wp_config_path, "w") as fd:
            fd.write(TEMPLATE_DLK_WP_CONFIG.format(**template_vars))
        (dlk_conf_dir / "modules.conf").symlink_to(self.dlk_path / "conf/modules.conf")

        self.proc = subprocess.Popen(
            [
                "php",
                "src/dalek",
            ],
            cwd=self.dlk_path,
            env={
                **os.environ,
                "DALEK_CONF_DIR": str(dlk_conf_dir),
                "DALEK_LOG_DIR": str(dlk_log_dir),
            },
        )

    def terminate(self) -> None:
        super().terminate()

    def kill(self) -> None:
        super().kill()

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        assert password
        subprocess.run(
            [
                "php",
                self.wp_cli_path,
                "user",
                "create",
                username,
                f"{username}@example.org",
                f"--user_pass={password}",
                f"--path={self.wp_path}",
            ],
            check=True,
        )


def get_irctest_controller_class() -> Type[DlkController]:
    return DlkController
