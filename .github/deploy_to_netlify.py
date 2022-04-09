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

output = subprocess.check_output(["netlify", "deploy", "--dir=dashboard/"]).decode()
print(output)

m = re.search("https://[^ ]*--[^ ]*netlify.app", output)
assert m
netlify_site_url = m.group(0)
target_url = f"{netlify_site_url}/index.xhtml"

statuses_url = github_event["repository"]["statuses_url"].format(sha=sha)

print(statuses_url)
payload = {
    "state": "success",
    "description": "irctest dashboard",
    "target_url": target_url,
}
request = urllib.request.Request(
    statuses_url,
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": os.environ["GITHUB_TOKEN"],
        "Content-Type": "text/json",
        "Accept": "application/vnd.github+json",
    },
)
print(request)

response = urllib.request.urlopen(request)

assert response.status == 201, response.read()
