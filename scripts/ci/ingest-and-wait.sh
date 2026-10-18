#!/bin/sh
# Trigger the ingest function once and wait until a completed raw-zone folder exists.
#   ENVIRONMENT=dev scripts/ci/ingest-and-wait.sh
# Needs: Azure CLI login, Storage Blob Data Reader (or better) on the lake, function key access.
set -eu

ENVIRONMENT="${ENVIRONMENT:?}"
RG="rg-ausold-${ENVIRONMENT}-aue"
OUT="$(az deployment sub show -n "ausold-${ENVIRONMENT}" --query properties.outputs -o json)"
FUNC="$(echo "$OUT" | jq -r .ingestFunctionName.value)"
LAKE="$(echo "$OUT" | jq -r .lakeStorageName.value)"

manifests() {
  az storage blob list --auth-mode login --account-name "$LAKE" -c raw --prefix nsw_psi/ \
    --query "[?ends_with(name, '_manifest.json')].name" -o tsv 2>/dev/null || true
}

before="$(manifests | wc -l | tr -d ' ')"
echo "Completed raw folders before: $before"

KEY=""
i=0
while [ -z "$KEY" ] && [ "$i" -lt 12 ]; do
  KEY="$(az functionapp keys list -g "$RG" -n "$FUNC" --query masterKey -o tsv 2>/dev/null || true)"
  [ -n "$KEY" ] || { i=$((i + 1)); sleep 15; }
done
[ -n "$KEY" ] || { echo "Could not read the function master key" >&2; exit 1; }
echo "::add-mask::$KEY"

i=0
while [ "$i" -lt 12 ]; do
  code="$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    -H "x-functions-key: $KEY" -H 'Content-Type: application/json' -d '{}' \
    "https://${FUNC}.azurewebsites.net/admin/functions/ingest_nsw_sales" || true)"
  [ "$code" = "202" ] && break
  echo "function not ready (HTTP $code), retrying..."
  i=$((i + 1)); sleep 20
done
[ "$code" = "202" ] || { echo "Could not trigger the ingest function" >&2; exit 1; }
echo "Ingest triggered."

# A completed folder (with its manifest) is the signal the download finished.
i=0
while [ "$i" -lt 60 ]; do
  now="$(manifests | wc -l | tr -d ' ')"
  if [ "$now" -gt 0 ]; then echo "Raw zone has $now completed folder(s)."; exit 0; fi
  i=$((i + 1)); sleep 20
done
cat >&2 <<EOF
No completed folder appeared in raw/nsw_psi after 20 minutes.
Check the function logs in Application Insights. If the source is unreachable, upload a CSV
manually with scripts/upload-csv.sh and re-run the data refresh.
EOF
exit 1
