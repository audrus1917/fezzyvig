#!/usr/bin/env bash

set -Eeuo pipefail

readonly API_BASE_URL="https://api.hh.ru"

usage() {
    cat <<'EOF'
Usage: hh-api.sh <path-or-url>

Environment variables:
  HH_ACCESS_TOKEN  HeadHunter OAuth access token (required)
  HH_USER_AGENT    Application name and developer contact (required)

Examples:
  hh-api.sh /me
  hh-api.sh '/employers/123/vacancies?page=0&per_page=20'
  hh-api.sh 'https://api.hh.ru/me'
EOF
}

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

: "${HH_ACCESS_TOKEN:?HH_ACCESS_TOKEN is required}"
: "${HH_USER_AGENT:?HH_USER_AGENT is required}"

case "$1" in
    /*)
        url="${API_BASE_URL}$1"
        ;;
    https://api.hh.ru | https://api.hh.ru/* | https://api.hh.ru\?*)
        url="$1"
        ;;
    *)
        printf 'Error: expected an api.hh.ru HTTPS URL or an absolute API path\n' >&2
        exit 2
        ;;
esac

curl \
    --silent \
    --show-error \
    --header "Authorization: Bearer ${HH_ACCESS_TOKEN}" \
    --header "HH-User-Agent: ${HH_USER_AGENT}" \
    --header 'Accept: application/json' \
    "$url"
