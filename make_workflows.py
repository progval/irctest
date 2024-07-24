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


def get_install_steps(*, software_config, software_id, version_flavor):
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
                "uses": "actions/checkout@v4",
                "with": {
                    "repository": software_config["repository"],
                    "ref": ref,
                    "path": path,
                },
            },
            *software_config.get("pre_deps", []),
            {
                "name": f"Build {name}",
                "run": script(software_config["build_script"]),
            },
        ]

    return install_steps


def get_build_job(*, software_config, software_id, version_flavor):
    if not software_config["separate_build_job"]:
        return None
    if "install_steps" in software_config:
        path = "placeholder"  # TODO: remove this
    else:
        path = software_config["path"]

    if software_config.get("cache", True):
        cache = [
            {
                "name": "Cache dependencies",
                "uses": "actions/cache@v4",
                "with": {
                    "path": f"~/.cache\n${{ github.workspace }}/{path}\n",
                    "key": "3-${{ runner.os }}-"
                    + software_id
                    + "-"
                    + version_flavor.value,
                },
            }
        ]
    else:
        cache = []

    install_steps = get_install_steps(
        software_config=software_config,
        software_id=software_id,
        version_flavor=version_flavor,
    )
    if install_steps is None:
        return None

    return {
        "runs-on": "ubuntu-22.04",
        "steps": [
            {
                "name": "Create directories",
                "run": "cd ~/; mkdir -p .local/ go/",
            },
            *cache,
            {"uses": "actions/checkout@v4"},
            {
                "name": "Set up Python 3.11",
                "uses": "actions/setup-python@v5",
                "with": {"python-version": 3.11},
            },
            *install_steps,
            *upload_steps(software_id),
        ],
    }


def get_test_job(*, config, test_config, test_id, version_flavor, jobs):
    if version_flavor.value in test_config.get("exclude_versions", []):
        return None

    env = ""
    needs = []
    downloads = []
    install_steps = []
    for software_id in test_config.get("software", []):
        software_config = config["software"][software_id]

        env += software_config.get("env", "") + " "
        if "prefix" in software_config:
            env += (
                f"PATH={software_config['prefix']}/sbin"
                f":{software_config['prefix']}/bin"
                f":{software_config['prefix']}"
                f":$PATH "
            )

        if software_config["separate_build_job"]:
            needs.append(f"build-{software_id}")
            downloads.append(
                {
                    "name": "Download build artefacts",
                    "uses": "actions/download-artifact@v4",
                    "with": {"name": f"installed-{software_id}", "path": "~"},
                }
            )
        else:
            new_install_steps = get_install_steps(
                software_config=software_config,
                software_id=software_id,
                version_flavor=version_flavor,
            )
            if new_install_steps is None:
                # This flavor does not need to be built
                return None
            install_steps.extend(new_install_steps)

    if not set(needs) <= jobs:
        # One of the dependencies does not exist for this flavor
        assert version_flavor != VersionFlavor.STABLE, set(needs) - jobs
        return None

    if downloads:
        unpack = [
            {
                "name": "Unpack artefacts",
                "run": r"cd ~; find -name 'artefacts-*.tar.gz' -exec tar -xzf '{}' \;",
            },
        ]
    else:
        # All the software is built in the same job, nothing to unpack
        unpack = []

    return {
        "runs-on": "ubuntu-22.04",
        "needs": needs,
        "steps": [
            {"uses": "actions/checkout@v4"},
            {
                "name": "Set up Python 3.11",
                "uses": "actions/setup-python@v5",
                "with": {"python-version": 3.11},
            },
            *downloads,
            *unpack,
            *install_steps,
            {
                "name": "Install system dependencies",
                "run": "sudo apt-get install atheme-services faketime",
            },
            {
                "name": "Install irctest dependencies",
                "run": script(
                    "python -m pip install --upgrade pip",
                    "pip install pytest pytest-xdist pytest-timeout -r requirements.txt",
                    *(
                        software_config["extra_deps"]
                        if "extra_deps" in software_config
                        else []
                    ),
                ),
            },
            {
                "name": "Test with pytest",
                "timeout-minutes": 30,
                "env": {
                    "IRCTEST_DEBUG": "${{ runner.debug }}",
                },
                "run": (
                    f"PYTEST_ARGS='--junit-xml pytest.xml --timeout 300' "
                    f"PATH=$HOME/.local/bin:$PATH "
                    f"{env}make {test_id}"
                ),
            },
            {
                "name": "Publish results",
                "if": "always()",
                "uses": "actions/upload-artifact@v4",
                "with": {
                    "name": f"pytest-results_{test_id}_{version_flavor.value}",
                    "path": "pytest.xml",
                },
            },
        ],
    }


def upload_steps(software_id):
    """Make a tarball (to preserve permissions) and upload"""
    return [
        {
            "name": "Make artefact tarball",
            "run": f"cd ~; tar -czf artefacts-{software_id}.tar.gz .local/ go/",
        },
        {
            "name": "Upload build artefacts",
            "uses": "actions/upload-artifact@v4",
            "with": {
                "name": f"installed-{software_id}",
                "path": "~/artefacts-*.tar.gz",
                # We only need it for the next step of the workflow, so let's
                # just delete it ASAP to avoid wasting resources
                "retention-days": 1,
            },
        },
    ]


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

    for test_id in config["tests"]:
        test_config = config["tests"][test_id]
        test_job = get_test_job(
            config=config,
            test_config=test_config,
            test_id=test_id,
            version_flavor=version_flavor,
            jobs=set(jobs),
        )
        if test_job is not None:
            jobs[f"test-{test_id}"] = test_job

    jobs["publish-test-results"] = {
        "name": "Publish Dashboard",
        "needs": sorted({f"test-{test_id}" for test_id in config["tests"]} & set(jobs)),
        "runs-on": "ubuntu-22.04",
        # the build-and-test job might be skipped, we don't need to run
        # this job then
        "if": "success() || failure()",
        "steps": [
            {"uses": "actions/checkout@v4"},
            {
                "name": "Download Artifacts",
                "uses": "actions/download-artifact@v4",
                "with": {"path": "artifacts"},
            },
            {
                "name": "Install dashboard dependencies",
                "run": script(
                    "python -m pip install --upgrade pip",
                    "pip install defusedxml docutils -r requirements.txt",
                ),
            },
            {
                "name": "Generate dashboard",
                "run": script(
                    "shopt -s globstar",
                    "python3 -m irctest.dashboard.format dashboard/ artifacts/**/*.xml",
                    "echo '/ /index.xhtml' > dashboard/_redirects",
                ),
            },
            {
                "name": "Install netlify-cli",
                "run": "npm i -g netlify-cli",
            },
            {
                "name": "Deploy to Netlify",
                "run": "./.github/deploy_to_netlify.py",
                "env": {
                    "NETLIFY_SITE_ID": "${{ secrets.NETLIFY_SITE_ID }}",
                    "NETLIFY_AUTH_TOKEN": "${{ secrets.NETLIFY_AUTH_TOKEN }}",
                    "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
                },
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
