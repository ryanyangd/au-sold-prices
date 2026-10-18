#!/bin/sh
# Upload a local cleaned-NSW CSV into the lake's raw zone of a deployed environment, e.g. for the
# first load or when the public source is stale or blocked. Then run the "Data refresh" workflow
# with "Trigger the ingest function first" unticked.
#   scripts/upload-csv.sh dev data/nsw-property-sales-data-updated20260914.csv
# Needs: az login and the Storage Blob Data Contributor role on the lake (Bicep grants it to
# ADMIN_OBJECT_ID). The file never enters git.
set -eu

ENVIRONMENT="${1:?usage: upload-csv.sh dev|prod <file.csv>}"
FILE="${2:?usage: upload-csv.sh dev|prod <file.csv>}"
[ -f "$FILE" ] || { echo "No such file: $FILE" >&2; exit 1; }
head -1 "$FILE" | grep -q 'Property locality' || { echo "Not a cleaned NSW sales CSV (header missing)" >&2; exit 1; }

LAKE="$(az deployment sub show -n "ausold-$ENVIRONMENT" --query properties.outputs.lakeStorageName.value -o tsv)"
STAMP="$(basename "$FILE" | grep -oE '[0-9]{8}' | tail -1 || true)"
[ -n "$STAMP" ] || STAMP="$(date -u +%Y%m%d)"
FOLDER="nsw_psi/$STAMP"

echo "Uploading to $LAKE/raw/$FOLDER/data.csv ..."
az storage blob upload --auth-mode login --account-name "$LAKE" -c raw -n "$FOLDER/data.csv" -f "$FILE" --overwrite --no-progress >/dev/null

MANIFEST="$(mktemp)"
printf '{"source":"manual-upload","file":"%s","uploaded_at":"%s"}\n' "$(basename "$FILE")" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$MANIFEST"
az storage blob upload --auth-mode login --account-name "$LAKE" -c raw -n "$FOLDER/_manifest.json" -f "$MANIFEST" --overwrite --no-progress >/dev/null
rm -f "$MANIFEST"

echo "Done. Next: gh workflow run data-refresh.yml -f environment=$ENVIRONMENT -f run_ingest=false"
