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


class Dumper(yaml.Dumper):
    pass


Dumper.add_representer(script, script_representer)


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


def get_build_job(*, software_config, software_id, version_flavor):
    name = software_config["name"]

    if "install_steps" in software_config:
        path = "placeholder"  # TODO: remove this
        install_steps = software_config["install_steps"][version_flavor.value]
        if install_steps is None:
            return None
    else:
        ref = software_config["refs"][version_flavor.value]
        if ref is None:
            return None
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

    if software_config.get("cache", True):
        cache = [
            {
                "name": "Cache dependencies",
                "uses": "actions/cache@v2",
                "with": {
                    "path": script("~/.cache", f"$GITHUB_WORKSPACE/{path}"),
                    "key": "${{ runner.os }}-"
                    + software_id
                    + "-"
                    + version_flavor.value,
                },
            }
        ]
    else:
        cache = []

    return {
        "runs-on": "ubuntu-latest",
        "steps": [
            *software_config.get("pre_deps", []),
            *cache,
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
                "name": "Upload build artefacts",
                "uses": "actions/upload-artifact@v2",
                "with": {
                    "name": f"installed-{software_id}",
                    "path": "~/.local",
                    # We only need it for the next step of the workflow, so let's
                    # just delete it ASAP to avoid wasting resources
                    "retention-days": 1,
                },
            },
        ],
    }


def get_test_job(*, software_config, software_id, version_flavor):
    name = software_config["name"]
    prefix = software_config.get("prefix", "~/.local")
    needs = [f"installed-{software_id}"]  # Built ~/.local
    env = software_config.get("env", {}).get(version_flavor.value, "")
    if env:
        env += " "

    if software_config.get("build_anope", False):
        needs.append(["installed-anope"])

    return {
        "runs-on": "ubuntu-latest",
        "needs": needs,
        "steps": [
            {"uses": "actions/checkout@v2"},
            {
                "name": "Set up Python 3.7",  # for irctest itself
                "uses": "actions/setup-python@v2",
                "with": {"python-version": 3.7},
            },
            {
                "name": "Download build artefacts",
                "uses": "actions/download-artifact@v2",
                "with": {
                    "name": f"installed {software_id}",
                },
            },
            {
                "name": "Test with pytest",
                "run": (
                    f"PYTEST_ARGS='--junit-xml pytest.xml' "
                    f"PATH={prefix}/bin:$HOME/.local/bin:$PATH "
                    f"{env}make {software_id}"
                ),
            },
            {
                "name": "Publish results",
                "if": "always()",
                "uses": "actions/upload-artifact@v2",
                "with": {
                    "name": f"pytest results {name} ({version_flavor.value})",
                    "path": "pytest.xml",
                },
            },
        ],
    }


def get_build_job_anope():
    return {
        "runs-on": "ubuntu-latest",
        "steps": [
            {
                "name": "Checkout Anope",
                "uses": "actions/checkout@v2",
                "with": {
                    "repository": "anope/anope",
                    "ref": "2.0.9",
                    "path": "anope",
                },
            },
            {
                "name": "Build Anope",
                "run": script(
                    "cd $GITHUB_WORKSPACE/anope/",
                    "cp $GITHUB_WORKSPACE/data/anope/* .",
                    "CFLAGS=-O0 ./Config -quick",
                    "make -C build -j 4",
                    "make -C build install",
                ),
            },
        ],
    }


def generate_workflow(config: dict, version_flavor: VersionFlavor):

    on: dict
    if version_flavor == VersionFlavor.STABLE:
        on = {"push": None, "pull_request": None}
    else:
        # Run every saturday and sunday 8:51 UTC, and every day at 17:51
        # (minute choosen at random, hours and days is so that I'm available
        # to fix bugs it detects)
        on = {
            "schedule": [
                {"cron": "51 8 * * 6"},
                {"cron": "51 8 * * 0"},
                {"cron": "51 17 * * *"},
            ],
            "workflow_dispatch": None,
        }

    jobs = {}

    for software_id in config["software"]:
        software_config = config["software"][software_id]
        build_job = get_build_job(
            software_config=software_config,
            software_id=software_id,
            version_flavor=version_flavor,
        )
        if build_job is not None:
            jobs[f"build-{software_id}"] = build_job
        test_job = get_test_job(
            software_config=software_config,
            software_id=software_id,
            version_flavor=version_flavor,
        )
        if test_job is not None:
            jobs[f"test-{software_id}"] = test_job

    jobs["build-anope"] = get_build_job_anope()
    jobs["publish-test-results"] = {
        "name": "Publish Unit Tests Results",
        "needs": [f"test-{software_id}" for software_id in config["software"]],
        "runs-on": "ubuntu-latest",
        # the build-and-test job might be skipped, we don't need to run
        # this job then
        "if": "success() || failure()",
        "steps": [
            {
                "name": "Download Artifacts",
                "uses": "actions/download-artifact@v2",
                "with": {"path": "artifacts"},
            },
            {
                "name": "Publish Unit Test Results",
                "uses": "EnricoMi/publish-unit-test-result-action@v1",
                "with": {"files": "artifacts/**/*.xml"},
            },
        ],
    }

    workflow = {
        "name": f"irctest with {version_flavor.value} versions",
        "on": on,
        "jobs": jobs,
    }

    workflow_filename = GH_WORKFLOW_DIR / f"test-{version_flavor.value}.yml"

    with open(workflow_filename, "wt") as fd:
        fd.write("# This file was auto-generated by make_workflows.py.\n")
        fd.write("# Do not edit it manually, modifications will be lost.\n\n")
        fd.write(yaml.dump(workflow, Dumper=Dumper))


def main():
    with open(DEFINITION_PATH) as fd:
        config = yaml.load(fd, Loader=yaml.Loader)

    generate_workflow(config, version_flavor=VersionFlavor.STABLE)
    generate_workflow(config, version_flavor=VersionFlavor.DEVEL)
    generate_workflow(config, version_flavor=VersionFlavor.DEVEL_RELEASE)


if __name__ == "__main__":
    main()
