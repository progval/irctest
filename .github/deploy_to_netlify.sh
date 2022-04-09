#!/usr/bin/env bash

set -e

# Inspired by https://github.com/rsotnychenko/deployment-status-update/blob/06e6b80279dbe8e8fbbcf68abd71db485a6c33e7/entrypoint.sh

OUTPUT=$(sh -c "netlify deploy --dir=dashboard/")
echo $OUTPUT

NETLIFY_SITE_URL=$(echo $OUTPUT | grep -o "https://.*--.*netlify.app")
echo $NETLIFY_SITE_URL
ENVIRONMENT_URL=$NETLIFY_SITE_URL/index.xhtml

get_from_event() {
  jq -r "$1" "${GITHUB_EVENT_PATH}"
}

GITHUB_API_DEPLOYMENTS_URL="$(get_from_event '.deployment.statuses_url')"

echo $GITHUB_API_DEPLOYMENTS_URL

curl --fail \
    -X POST "${GITHUB_API_DEPLOYMENTS_URL}" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Content-Type: text/json; charset=utf-8" \
    -H "Accept: application/vnd.github.ant-man-preview+json, application/vnd.github.flash-preview+json" \
    -d @- <<EOF
{
    "state": "success",
    "log_url": "${GITHUB_ACTIONS_RUN_URL}",
    "description": "irctest dashboard",
    "auto_inactive": false,
    "environment_url": "${ENVIRONMENT_URL}"
}
