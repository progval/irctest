import os
import random
import shutil
import subprocess
import tempfile
from typing import Optional, Type

import irctest
from irctest.basecontrollers import BaseServicesController, DirectoryBasedController
import irctest.cases
import irctest.runner

TEMPLATE_DLK_CONFIG = """
<?php global $cf;

include "languages/en_GB";

$cf = [
	'debugmode' => 'on',

	'sid' => '00A',
	'servicesname' => 'services.example.org',
	'network' => 'test network',

	'proto' => '{protocol}',

	'uplink' => '{server_hostname}',
	'port' => '{server_port}',
	'serverpassword' => 'password',

	/* SQL Config for the user database */
	'sqlip' => '',
	'sqlport' => '3306',
	'sqluser' => 'pifpaf',
	'sqlpass' => 'pifpaf',
	'sqldb' => 'pifpaf',
    'sqlsock' => '{mysql_socket}',

	'logchan' => '#services',
]
?>
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


define( 'ABSPATH', '{wp_directory}' );

/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */


/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
"""


class DlkController(BaseServicesController, DirectoryBasedController):
    """Mixin for server controllers that rely on DLK"""

    software_name = "DLK-Services"

    def run_sql(self, sql):
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

        self.wp_prefix = f"wp{random.randbytes(6).hex()}_"
        template_vars = dict(
            protocol=protocol,
            server_hostname=server_hostname,
            server_port=server_port,
            mysql_socket=mysql_socket,
            wp_directory="../wordpress",  # TODO configurable
            wp_prefix=self.wp_prefix,
        )

        # Configure Wordpress
        # wp_config_path = os.path.join(self.directory, "wp-config.php")
        wp_config_path = "../wordpress/wp-config.php"  # TODO: use the tempdir
        with open(wp_config_path, "w") as fd:
            fd.write(TEMPLATE_WP_CONFIG.format(**template_vars))
        print("=== config wordpress start")
        wp_proc = subprocess.run(
            [
                "php",
                "../wp-cli.phar",  # TODO should not be hardcoded
                "core",
                "install",
                "--url=http://localhost/",
                "--title=irctest site",
                "--admin_user=adminuser",
                "--admin_email=adminuser@example.org",
                f"--path=../wordpress",  # TODO should not be hardcoded
            ],
            check=True,
        )
        print("=== config wordpress end")

        # Configure Dlk
        dlk_config_path = "../Dalek-Services/conf/dalek.conf"
        with open(dlk_config_path, "w") as fd:  # TODO: use the tempdir
            fd.write(TEMPLATE_DLK_CONFIG.format(**template_vars))
        dlk_wp_config_path = "../Dalek-Services/src/wordpress/wordpress.conf"
        with open(dlk_wp_config_path, "w") as fd:  # TODO: use the tempdir
            fd.write(TEMPLATE_DLK_WP_CONFIG.format(**template_vars))

        # self.run_sql(INIT_SQL)
        self.proc = subprocess.Popen(
            [
                # "strace",
                # "-s", "10000",
                # "-f",
                "php",
                "src/dalek",
            ],
            cwd="../Dalek-Services/",
            # stdout=subprocess.DEVNULL,
            # stderr=subprocess.DEVNULL,
        )

    def terminate(self) -> None:
        print("===== terminate")
        super().terminate()

    def kill(self) -> None:
        print("===== kill")
        super().kill()

    def registerUser(
        self,
        case: irctest.cases.BaseServerTestCase,
        username: str,
        password: Optional[str] = None,
    ) -> None:
        assert password
        wp_proc = subprocess.run(
            [
                "php",
                "../wp-cli.phar",  # TODO should not be hardcoded
                "user",
                "create",
                username,
                f"{username}@example.org",
                f"--user_pass={password}",
                f"--path=../wordpress",  # TODO should not be hardcoded
            ],
            check=True,
        )


def get_irctest_controller_class() -> Type[DlkController]:
    return DlkController
