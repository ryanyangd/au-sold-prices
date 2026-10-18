#!/bin/sh
# Post-deploy smoke test: the API and the web app answer, and search returns JSON.
#   scripts/ci/smoke.sh <api-url> <web-url>
set -eu

API="${1:?api url}"
WEB="${2:?web url}"

retry() { # description command...
  desc="$1"; shift
  i=0
  while [ "$i" -lt 30 ]; do
    if "$@" >/dev/null 2>&1; then echo "ok: $desc"; return 0; fi
    i=$((i + 1)); sleep 10
  done
  echo "FAILED: $desc" >&2
  return 1
}

retry "API liveness" curl -fsS "$API/health"
retry "API database readiness" curl -fsS "$API/health/ready"
retry "web home page" curl -fsS "$WEB/"
retry "address search returns JSON" sh -c "curl -fsS '$API/search/addresses?q=george' | grep -q '\"results\"'"
