#!/bin/sh
# Configure the GitHub side of deployments with the gh CLI.
#   export AZURE_CLIENT_ID=... AZURE_TENANT_ID=... AZURE_SUBSCRIPTION_ID=... \
#          DEPLOYER_OBJECT_ID=... ADMIN_OBJECT_ID=... ALERT_EMAIL=you@example.com
#   scripts/github-setup.sh dev        (then prod)
#
# Creates the GitHub environments `<env>` (config) and `<env>-approval` (approval gate; `prod`
# needs you as a required reviewer), the labels the workflows use, and the environment
# variables and secrets. A Postgres admin password is generated if none exists yet.
# Optional variables: ENTRA_TENANT_ID ENTRA_TENANT_SUBDOMAIN ENTRA_API_AUDIENCE
# NEXT_PUBLIC_ENTRA_CLIENT_ID NEXT_PUBLIC_ENTRA_AUTHORITY NEXT_PUBLIC_ENTRA_API_SCOPE
# STRIPE_PRICE_MONTHLY STRIPE_PRICE_ANNUAL; optional secrets: STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET.
set -eu

ENVIRONMENT="${1:?usage: github-setup.sh dev|prod}"
command -v gh >/dev/null 2>&1 || { echo "GitHub CLI (gh) not found. Install it and run: gh auth login" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Not logged in to GitHub. Run: gh auth login" >&2; exit 1; }
cd "$(dirname "$0")/.."
REPO="${GITHUB_REPO:-$(git config --get remote.origin.url 2>/dev/null | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##' || true)}"
[ -n "$REPO" ] || { echo "Cannot work out the GitHub repo. Set GITHUB_REPO=owner/name." >&2; exit 1; }
: "${AZURE_CLIENT_ID:?run scripts/azure-bootstrap.sh first and paste its export lines}" "${AZURE_TENANT_ID:?}" "${AZURE_SUBSCRIPTION_ID:?}" "${ALERT_EMAIL:?export ALERT_EMAIL=you@example.com}"

USER_ID="$(gh api user --jq .id)"

create_environment() { # name with_reviewer(true|false)
  if [ "$2" = "true" ]; then
    BODY="{\"reviewers\":[{\"type\":\"User\",\"id\":$USER_ID}],\"deployment_branch_policy\":{\"protected_branches\":false,\"custom_branch_policies\":true}}"
  else
    BODY='{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}'
  fi
  if echo "$BODY" | gh api -X PUT "repos/$REPO/environments/$1" --input - >/dev/null 2>/tmp/gh-env.err; then
    gh api -X POST "repos/$REPO/environments/$1/deployment-branch-policies" -f name=main -f type=branch >/dev/null 2>&1 || true
    echo "environment $1: ready"
  else
    echo "environment $1: FAILED ($(tr -d '\n' </tmp/gh-env.err))" >&2
    echo "  Required reviewers on private repos need GitHub Pro/Team/Enterprise." >&2
    return 1
  fi
}

create_environment "$ENVIRONMENT" false
if [ "$ENVIRONMENT" = "prod" ]; then create_environment "prod-approval" true; else create_environment "dev-approval" false; fi

for LABEL in "bug:d73a4a" "deploy-failure:b60205" "data-pipeline:0e8a16"; do
  gh label create "${LABEL%%:*}" --color "${LABEL##*:}" --repo "$REPO" >/dev/null 2>&1 || true
done

set_var() { # name value
  [ -z "$2" ] || { gh variable set "$1" --env "$ENVIRONMENT" --repo "$REPO" --body "$2" >/dev/null; echo "  var $1"; }
}
set_secret() { # name value
  [ -z "$2" ] || { printf '%s' "$2" | gh secret set "$1" --env "$ENVIRONMENT" --repo "$REPO" >/dev/null; echo "  secret $1"; }
}

echo "Variables and secrets for $ENVIRONMENT:"
set_var AZURE_CLIENT_ID "$AZURE_CLIENT_ID"
set_var AZURE_TENANT_ID "$AZURE_TENANT_ID"
set_var AZURE_SUBSCRIPTION_ID "$AZURE_SUBSCRIPTION_ID"
set_var ALERT_EMAIL "$ALERT_EMAIL"
set_var DEPLOYER_OBJECT_ID "${DEPLOYER_OBJECT_ID:-}"
set_var ADMIN_OBJECT_ID "${ADMIN_OBJECT_ID:-}"
for NAME in ENTRA_TENANT_ID ENTRA_TENANT_SUBDOMAIN ENTRA_API_AUDIENCE NEXT_PUBLIC_ENTRA_CLIENT_ID \
  NEXT_PUBLIC_ENTRA_AUTHORITY NEXT_PUBLIC_ENTRA_API_SCOPE STRIPE_PRICE_MONTHLY STRIPE_PRICE_ANNUAL; do
  eval "VALUE=\${$NAME:-}"
  set_var "$NAME" "$VALUE"
done

if ! gh secret list --env "$ENVIRONMENT" --repo "$REPO" | grep -q '^PG_ADMIN_PASSWORD'; then
  set_secret PG_ADMIN_PASSWORD "$(openssl rand -base64 33 | tr -d '/+=\n' | cut -c1-32)Aa1"
else
  echo "  secret PG_ADMIN_PASSWORD (kept; already set)"
fi
set_secret STRIPE_SECRET_KEY "${STRIPE_SECRET_KEY:-}"
set_secret STRIPE_WEBHOOK_SECRET "${STRIPE_WEBHOOK_SECRET:-}"

echo "Done. Next: run the Deploy workflow (Actions > Deploy > Run workflow)."
