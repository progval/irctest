"""
This script reads the compact workflows.yml file, and and generates files in
.github/workflows/ suitable for the limited expressivity of GitHub's workflow
definition language.

The point is that we had/have a lot of duplications between files in
.github/workflows/, so we use this script to make it easier to update them
and keep them in sync.
"""

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


class Dumper(yaml.Dumper):
    pass


Dumper.add_representer(script, script_representer)


def generate_workflow(config, software_id):
    software_config = config["software"][software_id]
    path = software_config["path"]
    name = software_config["name"]
    prefix = software_config.get("prefix", "~/.local")
    workflow = {
        "name": f"irctest with {name}",
        "on": {"push": None, "pull_request": None},
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
                        ),
                    },
                    {
                        "name": f"Checkout {name}",
                        "uses": "actions/checkout@v2",
                        "with": {
                            "repository": software_config["repository"],
                            "ref": software_config["ref"],
                            "path": path,
                        },
                    },
                    {
                        "name": f"Build {name}",
                        "run": script(software_config["build_script"]),
                    },
                    {
                        "name": "Test with pytest",
                        "run": f"PATH={prefix}/bin:$PATH make {software_id}",
                    },
                ],
            }
        },
    }

    with open(GH_WORKFLOW_DIR / f"{software_id}.yml", "wt") as fd:
        fd.write("# This file was auto-generated by make_workflows.py.\n")
        fd.write("# Do not edit it manually, modifications will be lost.\n\n")
        fd.write(yaml.dump(workflow, Dumper=Dumper))


def main():
    with open(DEFINITION_PATH) as fd:
        config = yaml.load(fd, Loader=yaml.Loader)

    for software_id in config["software"]:
        generate_workflow(config, software_id)


if __name__ == "__main__":
    main()
