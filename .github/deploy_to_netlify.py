#!/usr/bin/env python3

import json
import os
import pprint
import re
import subprocess
import urllib.request

with open(os.environ["GITHUB_EVENT_PATH"]) as fd:
    github_event = json.load(fd)

pprint.pprint(github_event)

sha = github_event["head_commit"]["id"]
ref = github_event["ref"]

command = ["netlify", "deploy", "--dir=dashboard/"]
m = re.match("refs/pull/([0-9]+)/head", ref)
if m:
    pr_id = m.group(1)
    command.append(f"--alias pr-{pr_id}-{sha}")
else:
    m = re.match("refs/heads/(.*)", ref)
    if m:
        branch = m.group(1)
        if branch in ("main", "master"):
            command.append("--prod")
        else:
            # Aliases can't exceed 37 chars
            command.append(f"--alias br-{branch[0:23]}-{sha[0:10]}")
    else:
        # TODO
        pass


proc = subprocess.run(command, capture_output=True, stdout=subprocess.PIPE)

output = proc.stdout.decode()
print(output)
assert proc.returncode == 0, output

m = re.search("https://[^ ]*--[^ ]*netlify.app", output)
assert m
netlify_site_url = m.group(0)
target_url = f"{netlify_site_url}/index.xhtml"

statuses_url = github_event["repository"]["statuses_url"].format(sha=sha)

payload = {
    "state": "success",
    "context": "summary",
    "description": "irctest dashboard",
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
