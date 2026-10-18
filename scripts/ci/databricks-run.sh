#!/bin/sh
# Deploy and run the Databricks pipeline job for one environment.
#   ENVIRONMENT=dev AUSOLD_PG_PASSWORD=... ALERT_EMAIL=... scripts/ci/databricks-run.sh
# Needs: Azure CLI login (Contributor on the workspace), the `databricks` CLI, `jq`.
# The identity signs in to the workspace through its Azure resource ID, so no Databricks token
# or manual workspace user setup is needed.
set -eu

ENVIRONMENT="${ENVIRONMENT:?}"
: "${AUSOLD_PG_PASSWORD:?PG_ADMIN_PASSWORD secret is required}"
: "${ALERT_EMAIL:?ALERT_EMAIL variable is required}"

OUT="$(az deployment sub show -n "ausold-${ENVIRONMENT}" --query properties.outputs -o json)"
CATALOG="$(echo "$OUT" | jq -r .databricksCatalog.value)"
PG_HOST="$(echo "$OUT" | jq -r .postgresHost.value)"
DATABRICKS_HOST="https://$(echo "$OUT" | jq -r .databricksWorkspaceUrl.value)"
DATABRICKS_AZURE_RESOURCE_ID="$(echo "$OUT" | jq -r .databricksWorkspaceId.value)"
DATABRICKS_AUTH_TYPE=azure-cli
export DATABRICKS_HOST DATABRICKS_AZURE_RESOURCE_ID DATABRICKS_AUTH_TYPE

URL="postgresql://ausoldadmin:${AUSOLD_PG_PASSWORD}@${PG_HOST}:5432/ausold?sslmode=require"
echo "::add-mask::$URL"
databricks secrets create-scope ausold 2>/dev/null || echo "secret scope ausold exists"
databricks secrets put-secret ausold database-url --string-value "$URL"

cd pipelines/databricks
databricks bundle deploy -t "$ENVIRONMENT" --var="catalog=$CATALOG" --var="alert_email=$ALERT_EMAIL"
databricks bundle run -t "$ENVIRONMENT" --var="catalog=$CATALOG" --var="alert_email=$ALERT_EMAIL" nsw_sales_pipeline
