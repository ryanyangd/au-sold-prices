#!/bin/sh
# One-time Azure setup for GitHub Actions deployments (passwordless, via OIDC).
#   az login && az account set --subscription <subscription-for-this-environment>
#   scripts/azure-bootstrap.sh dev      (then again for prod, in the prod subscription)
#
# Creates an app registration + service principal for the environment, trusts GitHub's OIDC
# tokens for the repo's `<env>` GitHub environment, and grants it Contributor and User Access
# Administrator on the subscription (Bicep creates role assignments). Prints the values that
# scripts/github-setup.sh needs. Safe to re-run.
set -eu

ENVIRONMENT="${1:?usage: azure-bootstrap.sh dev|prod}"

command -v az >/dev/null 2>&1 || { echo "Azure CLI (az) not found. Install it or add it to PATH (Homebrew: /opt/homebrew/bin)." >&2; exit 1; }
az account show >/dev/null 2>&1 || { echo "Not logged in. Run: az login" >&2; exit 1; }
# Resolve the repo relative to this script so it works from any directory.
cd "$(dirname "$0")/.."
REPO="${GITHUB_REPO:-$(git config --get remote.origin.url 2>/dev/null | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##' || true)}"
[ -n "$REPO" ] || { echo "Cannot work out the GitHub repo. Set GITHUB_REPO=owner/name." >&2; exit 1; }
SUBSCRIPTION="$(az account show --query id -o tsv)"
TENANT="$(az account show --query tenantId -o tsv)"
NAME="sp-github-ausold-$ENVIRONMENT"

# Entra objects take a few seconds to become visible; retry instead of failing.
retry() { # command...
  n=0
  until "$@"; do
    n=$((n + 1))
    [ "$n" -lt 6 ] || { echo "Failed after $n attempts: $*" >&2; return 1; }
    echo "  waiting for Entra to catch up (attempt $n)..." >&2
    sleep 10
  done
}

echo "Environment:  $ENVIRONMENT"
echo "Repository:   $REPO"
echo "Subscription: $SUBSCRIPTION ($(az account show --query name -o tsv))"

APP_ID="$(az ad app list --display-name "$NAME" --query '[0].appId' -o tsv)"
if [ -z "$APP_ID" ]; then
  APP_ID="$(az ad app create --display-name "$NAME" --query appId -o tsv)"
  echo "Created app registration $NAME"
fi

SP_OBJECT_ID="$(az ad sp show --id "$APP_ID" --query id -o tsv 2>/dev/null || true)"
if [ -z "$SP_OBJECT_ID" ]; then
  retry az ad sp create --id "$APP_ID" >/dev/null
  SP_OBJECT_ID="$(retry az ad sp show --id "$APP_ID" --query id -o tsv)"
fi

SUBJECT="repo:${REPO}:environment:${ENVIRONMENT}"
EXISTING="$(az ad app federated-credential list --id "$APP_ID" --query "[?subject=='$SUBJECT'].name" -o tsv)"
if [ -z "$EXISTING" ]; then
  retry az ad app federated-credential create --id "$APP_ID" --parameters "{
    \"name\": \"github-$ENVIRONMENT\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"$SUBJECT\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" >/dev/null
  echo "Trusted GitHub OIDC subject $SUBJECT"
fi

for ROLE in "Contributor" "User Access Administrator"; do
  HAS="$(az role assignment list --assignee "$SP_OBJECT_ID" --role "$ROLE" --scope "/subscriptions/$SUBSCRIPTION" --query 'length(@)' -o tsv 2>/dev/null || echo 0)"
  if [ "${HAS:-0}" -eq 0 ]; then
    retry az role assignment create --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal \
      --role "$ROLE" --scope "/subscriptions/$SUBSCRIPTION" >/dev/null
  fi
done
echo "Granted Contributor and User Access Administrator"

ADMIN_OBJECT_ID="$(az ad signed-in-user show --query id -o tsv 2>/dev/null || true)"

cat <<EOF

Copy these into your shell, then run: scripts/github-setup.sh $ENVIRONMENT

export AZURE_CLIENT_ID=$APP_ID
export AZURE_TENANT_ID=$TENANT
export AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION
export DEPLOYER_OBJECT_ID=$SP_OBJECT_ID
export ADMIN_OBJECT_ID=$ADMIN_OBJECT_ID
EOF
