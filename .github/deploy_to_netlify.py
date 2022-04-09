#!/usr/bin/env python3

import json
import os
import re
import subprocess
import urllib.request

with open(os.environ["GITHUB_EVENT_PATH"]) as fd:
    github_event = json.load(fd)

context_suffix = ""

command = ["netlify", "deploy", "--dir=dashboard/"]
if "pull_request" in github_event and "number" in github_event:
    pr_number = github_event["number"]
    sha = github_event["after"]
    # Aliases can't exceed 37 chars
    command.extend(["--alias", f"pr-{pr_number}-{sha[0:10]}"])
    context_suffix = " (pull_request)"
else:
    ref = github_event["ref"]
    m = re.match("refs/heads/(.*)", ref)
    if m:
        branch = m.group(1)
        sha = github_event["head_commit"]["id"]

        command.extend(["--alias", f"br-{branch[0:23]}-{sha[0:10]}"])

        if branch in ("main", "master"):
            command.extend(["--prod"])
        else:
            context_suffix = " (push)"
    else:
        # TODO
        pass


proc = subprocess.run(command, capture_output=True)

output = proc.stdout.decode()
assert proc.returncode == 0, (output, proc.stderr.decode())

m = re.search("https://[^ ]*--[^ ]*netlify.app", output)
assert m
netlify_site_url = m.group(0)
target_url = f"{netlify_site_url}/index.xhtml"


def send_status() -> None:
    statuses_url = github_event["repository"]["statuses_url"].format(sha=sha)

    payload = {
        "state": "success",
        "context": f"Dashboard{context_suffix}",
        "description": "Table of all test results",
        "target_url": target_url,
    }
    request = urllib.request.Request(
        statuses_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f'token {os.environ["GITHUB_TOKEN"]}',
            "Content-Type": "text/json",
            "Accept": "application/vnd.github+json",
        },
    )

    response = urllib.request.urlopen(request)

    assert response.status == 201, response.read()


send_status()


def send_pr_comment() -> None:
    comments_url = github_event["pull_request"]["_links"]["comments"]["href"]

    payload = {
        "body": f"[Test results]({target_url})",
    }
    request = urllib.request.Request(
        comments_url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f'token {os.environ["GITHUB_TOKEN"]}',
            "Content-Type": "text/json",
            "Accept": "application/vnd.github+json",
        },
    )

    response = urllib.request.urlopen(request)

    assert response.status == 201, response.read()


if "pull_request" in github_event:
    send_pr_comment()
