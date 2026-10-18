#!/bin/sh
# Prepare Unity Catalog and the Postgres secret, then deploy and run the Databricks job.
#   ENVIRONMENT=dev scripts/ci/databricks-run.sh
# Needs: Azure CLI login as the identity that created the workspace, `databricks` CLI, and
# `pip install databricks-sdk`.
set -eu

ENVIRONMENT="${ENVIRONMENT:?}"
OUT="$(az deployment sub show -n "ausold-${ENVIRONMENT}" --query properties.outputs -o json)"
LAKE_ACCOUNT="$(echo "$OUT" | jq -r .lakeStorageName.value)"
ACCESS_CONNECTOR_ID="$(echo "$OUT" | jq -r .databricksAccessConnectorId.value)"
PG_HOST="$(echo "$OUT" | jq -r .postgresHost.value)"
DATABRICKS_HOST="https://$(echo "$OUT" | jq -r .databricksWorkspaceUrl.value)"
export LAKE_ACCOUNT ACCESS_CONNECTOR_ID DATABRICKS_HOST
export DATABRICKS_AUTH_TYPE=azure-cli

python pipelines/databricks/bootstrap_unity_catalog.py

databricks secrets create-scope ausold 2>/dev/null || echo "secret scope ausold exists"
# Built here instead of read from Key Vault, which may have public access disabled by policy.
: "${AUSOLD_PG_PASSWORD:?PG_ADMIN_PASSWORD secret is required}"
URL="postgresql://ausoldadmin:${AUSOLD_PG_PASSWORD}@${PG_HOST}:5432/ausold?sslmode=require"
echo "::add-mask::$URL"
databricks secrets put-secret ausold database-url --string-value "$URL"

cd pipelines/databricks
databricks bundle deploy -t "$ENVIRONMENT" --var="lake_account=$LAKE_ACCOUNT"
databricks bundle run -t "$ENVIRONMENT" --var="lake_account=$LAKE_ACCOUNT" nsw_sales_pipeline
