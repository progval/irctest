"""
This script reads the compact workflows.yml file, and and generates files in
.github/workflows/ suitable for the limited expressivity of GitHub's workflow
definition language.

The point is that we had/have a lot of duplications between files in
.github/workflows/, so we use this script to make it easier to update them
and keep them in sync.
"""

import enum
import pathlib

import yaml

ROOT_PATH = pathlib.Path(__file__).parent
DEFINITION_PATH = ROOT_PATH / "workflows.yml"
GH_WORKFLOW_DIR = ROOT_PATH / ".github" / "workflows"


class script:
    def __init__(self, *lines):
        self.data = "\n".join(lines)


def script_representer(dumper, data: script):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data.data, style="|")


class cronline(str):
    pass


def cronline_representer(dumper, data: cronline):
    """Forces cron lines to be quoted, because GitHub needs it for some reason."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")


class Dumper(yaml.Dumper):
    pass


Dumper.add_representer(script, script_representer)
Dumper.add_representer(cronline, cronline_representer)


class VersionFlavor(enum.Enum):
    STABLE = "stable"
    """A statically defined version, that we already tested irctest on.
    This is ran on PRs and master, because failure guarantees it's a bug in
    the new irctest commit/PR."""
    RELEASE = "release"
    """The last release of the project. This should usually pass.
    We don't currently use this."""
    DEVEL = "devel"
    """The last commit of the project. This allows us to catch bugs in other
    software early in their development process."""
    DEVEL_RELEASE = "devel_release"
    """Ditto, but if the project uses a specific branch for their current
    release series, it uses that branch instead"""


def generate_workflow(config: dict, software_id: str, version_flavor: VersionFlavor):
    software_config = config["software"][software_id]
    name = software_config["name"]
    prefix = software_config.get("prefix", "~/.local")

    if "install_steps" in software_config:
        path = "placeholder"  # TODO: remove this
        install_steps = software_config["install_steps"][version_flavor.value]
        if install_steps is None:
            return
    else:
        ref = software_config["refs"][version_flavor.value]
        if ref is None:
            return
        path = software_config["path"]
        install_steps = [
            {
                "name": f"Checkout {name}",
                "uses": "actions/checkout@v2",
                "with": {
                    "repository": software_config["repository"],
                    "ref": ref,
                    "path": path,
                },
            },
            {
                "name": f"Build {name}",
                "run": script(software_config["build_script"]),
            },
        ]

    on: dict
    if version_flavor == VersionFlavor.STABLE:
        on = {"push": None, "pull_request": None}
    else:
        # Run every saturday and sunday 8:51 UTC, and every day at 17:51
        # (minute choosen at random, hours and days is so that I'm available
        # to fix bugs it detects)
        on = {
            "schedule": [
                {"cron": cronline("51 8 * * 6")},
                {"cron": cronline("51 8 * * 0")},
                {"cron": cronline("51 17 * * *")},
            ]
        }

    workflow = {
        "name": f"irctest with {name}",
        "on": on,
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v2"},
                    {
                        "name": "Set up Python 3.7",  # for irctest itself
                        "uses": "actions/setup-python@v2",
                        "with": {"python-version": 3.7},
                    },
                    *software_config.get("pre_deps", []),
                    {
                        "name": "Cache dependencies",
                        "uses": "actions/cache@v2",
                        "with": {
                            "path": script("~/.cache", f"$GITHUB_WORKSPACE/{path}"),
                            "key": "${{ runner.os }}-" + software_id,
                        },
                    },
                    {
                        "name": "Install dependencies",
                        "run": script(
                            "sudo apt-get install atheme-services",
                            "python -m pip install --upgrade pip",
                            "pip install pytest -r requirements.txt",
                            *(
                                software_config["extra_deps"]
                                if "extra_deps" in software_config
                                else []
                            ),
                        ),
                    },
                    *install_steps,
                    {
                        "name": "Test with pytest",
                        "run": f"PATH={prefix}/bin:$PATH make {software_id}",
                    },
                ],
            }
        },
    }

    if version_flavor == VersionFlavor.STABLE:
        workflow_filename = GH_WORKFLOW_DIR / f"{software_id}.yml"
    else:
        workflow_filename = (
            GH_WORKFLOW_DIR / f"{software_id}_{version_flavor.value}.yml"
        )

    with open(workflow_filename, "wt") as fd:
        fd.write("# This file was auto-generated by make_workflows.py.\n")
        fd.write("# Do not edit it manually, modifications will be lost.\n\n")
        fd.write(yaml.dump(workflow, Dumper=Dumper).replace("'on':", "on:"))


def main():
    with open(DEFINITION_PATH) as fd:
        config = yaml.load(fd, Loader=yaml.Loader)

    for software_id in config["software"]:
        generate_workflow(config, software_id, version_flavor=VersionFlavor.STABLE)
        generate_workflow(config, software_id, version_flavor=VersionFlavor.DEVEL)
        generate_workflow(
            config, software_id, version_flavor=VersionFlavor.DEVEL_RELEASE
        )


if __name__ == "__main__":
    main()
