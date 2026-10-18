#!/bin/sh
# Deploy (or preview) infra/main.bicep for one environment. Used by the deploy workflow.
#   scripts/ci/bicep-deploy.sh what-if|create
# Reads configuration from environment variables; see infra/main.bicepparam. On `create` it
# writes the deployment outputs to $OUTPUTS_FILE (default: deployment-outputs.json).
set -eu

MODE="${1:?usage: bicep-deploy.sh what-if|create}"
ENVIRONMENT="${AUSOLD_ENVIRONMENT:?AUSOLD_ENVIRONMENT is required (dev|prod)}"
LOCATION="${AUSOLD_LOCATION:-australiaeast}"
RG="rg-ausold-${ENVIRONMENT}-aue"
OUTPUTS_FILE="${OUTPUTS_FILE:-deployment-outputs.json}"

[ -n "${AUSOLD_PG_PASSWORD:-}" ] || { echo "PG_ADMIN_PASSWORD secret is missing for $ENVIRONMENT" >&2; exit 1; }
if [ "$ENVIRONMENT" = "prod" ] && [ -z "${ENTRA_TENANT_ID:-}" ]; then
  echo "prod requires Entra External ID (set the ENTRA_* variables on the prod environment)." >&2
  exit 1
fi

# Keep the images that are already running so an infra-only run never resets the apps.
current_image() {
  az containerapp show -g "$RG" -n "$1" --query 'properties.template.containers[0].image' -o tsv 2>/dev/null || true
}
if [ -z "${AUSOLD_API_IMAGE:-}" ]; then
  img="$(current_image "ca-ausold-api-${ENVIRONMENT}")"
  [ -z "$img" ] || export AUSOLD_API_IMAGE="$img"
fi
if [ -z "${AUSOLD_WEB_IMAGE:-}" ]; then
  img="$(current_image "ca-ausold-web-${ENVIRONMENT}")"
  [ -z "$img" ] || export AUSOLD_WEB_IMAGE="$img"
fi

# First of the current month, so a new environment gets a valid budget start date.
export AUSOLD_BUDGET_START="${AUSOLD_BUDGET_START:-$(date -u +%Y-%m-01)}"

case "$MODE" in
  what-if)
    az deployment sub what-if -n "ausold-${ENVIRONMENT}-whatif" -l "$LOCATION" \
      -f infra/main.bicep -p infra/main.bicepparam --no-pretty-print --result-format ResourceIdOnly \
      --query 'changes[].{change:changeType, resource:resourceId}' -o table
    ;;
  create)
    az deployment sub create -n "ausold-${ENVIRONMENT}" -l "$LOCATION" \
      -f infra/main.bicep -p infra/main.bicepparam \
      --query properties.outputs -o json >"$OUTPUTS_FILE"
    echo "Outputs written to $OUTPUTS_FILE"
    ;;
  *) echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
