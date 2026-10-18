#!/bin/sh
# Start the environment's PostgreSQL server if it has been stopped, and wait until it is ready.
#   scripts/ci/ensure-postgres.sh dev|prod
# Some subscriptions run a Microsoft-managed automation that stops idle dev resources overnight
# (this project's did, which made search hang). Needs an Azure CLI login with Contributor.
set -eu

ENVIRONMENT="${1:?usage: ensure-postgres.sh dev|prod}"
RG="rg-ausold-${ENVIRONMENT}-aue"

if [ "$(az group exists -n "$RG")" != "true" ]; then
  echo "Resource group $RG does not exist yet; nothing to do."
  exit 0
fi

SERVER="$(az postgres flexible-server list -g "$RG" --query '[0].name' -o tsv)"
[ -n "$SERVER" ] || { echo "No Postgres server in $RG; nothing to do."; exit 0; }

state() { az postgres flexible-server show -g "$RG" -n "$SERVER" --query state -o tsv; }

CURRENT="$(state)"
echo "$SERVER is $CURRENT"
if [ "$CURRENT" = "Stopped" ] || [ "$CURRENT" = "Disabled" ]; then
  echo "Starting $SERVER..."
  az postgres flexible-server start -g "$RG" -n "$SERVER"
fi

i=0
until [ "$(state)" = "Ready" ]; do
  i=$((i + 1))
  [ "$i" -le 40 ] || { echo "$SERVER did not become Ready in time (state: $(state))" >&2; exit 1; }
  sleep 15
done
echo "$SERVER is Ready"
