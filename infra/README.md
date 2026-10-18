# Infrastructure (Bicep)

The normal way to deploy is the GitHub Actions workflow; see [docs/deployment.md](../docs/deployment.md).
This file describes the Bicep itself and the manual commands. One parameter file serves both
environments: set `AUSOLD_ENVIRONMENT=dev|prod` (default `dev`).

## What is deployed (per environment, one resource group `rg-ausold-<env>-aue`)

| Resource | Purpose |
|---|---|
| Databricks workspace (premium) | Runs the whole data pipeline as a scheduled job on serverless compute |
| PostgreSQL Flexible Server 16 | Serving database (`serving` schema from the pipeline, `app` schema for users/subscriptions); `pg_trgm` allow-listed |
| Container Registry (Basic), Container Apps environment, `api` and `web` apps | The FastAPI service and the Next.js frontend |
| Log Analytics workspace | Container Apps logs |
| Budget | Email alerts at 50/80/100% actual and 100% forecast (does not stop spend) |

**No customer storage account and no Key Vault.** The pipeline stores its raw files, bronze,
silver and gold tables in the Unity Catalog catalog that Azure Databricks creates with every
workspace (named after it, `dbw-ausold-dev` becomes `dbw_ausold_dev`), which lives in
Databricks-managed storage. This also keeps the design working in subscriptions whose policy
forces storage accounts and Key Vault to have public network access disabled (the MCAPS policy in
this project's subscription did exactly that). Secrets are passed as secure Bicep parameters,
stored as Container Apps secrets, and held in GitHub environment secrets.

Known v1 shortcuts to revisit before real customers: Postgres allows connections from Azure
services (TLS only) and the API uses the admin login; there is no private networking, Front Door/
WAF or custom domain yet.

## Deploy manually (to a new subscription)

```sh
az login
az account set --subscription <subscription-id>
export AUSOLD_ENVIRONMENT=dev            # or prod
export AUSOLD_ALERT_EMAIL=you@example.com
export AUSOLD_PG_PASSWORD="$(openssl rand -base64 33 | tr -d '/+=\n' | cut -c1-32)Aa1"   # keep it
# Optional: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_MONTHLY, STRIPE_PRICE_ANNUAL,
# ENTRA_TENANT_ID, ENTRA_TENANT_SUBDOMAIN, ENTRA_API_AUDIENCE (prod requires the ENTRA_* values)

sh scripts/ci/bicep-deploy.sh what-if
sh scripts/ci/bicep-deploy.sh create     # outputs: deployment-outputs.json
```

Register these resource providers first if the subscription is new: `Microsoft.Databricks`,
`Microsoft.DBforPostgreSQL`, `Microsoft.ContainerRegistry`, `Microsoft.App`,
`Microsoft.ManagedIdentity`, `Microsoft.OperationalInsights`, `Microsoft.Consumption`.

The first deployment runs a placeholder image in the apps. Build and release the real images
(the workflow does this for you):

```sh
REG=<registryName output>
az acr build -r $REG -t ausold-api:v1 -f docker/api.Dockerfile .
az acr build -r $REG -t ausold-web:v1 --build-arg NEXT_PUBLIC_API_BASE_URL=<apiUrl output> apps/web
AUSOLD_API_IMAGE=$REG.azurecr.io/ausold-api:v1 AUSOLD_WEB_IMAGE=$REG.azurecr.io/ausold-web:v1 \
  sh scripts/ci/bicep-deploy.sh create
```

## Run the data pipeline manually

```sh
ENVIRONMENT=dev ALERT_EMAIL=you@example.com AUSOLD_PG_PASSWORD=... sh scripts/ci/databricks-run.sh
```

This needs the `databricks` CLI (`brew install databricks/tap/databricks`) and an Azure login with
Contributor on the workspace. It signs in through the workspace's Azure resource ID, so no
Databricks token is needed. The job (`nsw-sales-pipeline-<env>`) has four tasks: `ingest`
(download the source file into a volume), `bronze`, `silver_gold` and `load_serving` (swap the
tables into Postgres). It also runs daily at 06:00 Sydney time and emails `ALERT_EMAIL` on failure.

To load your own CSV instead of (or before) the public source:

```sh
pip install databricks-sdk
python scripts/upload_csv.py dev data/nsw-property-sales-data-updated20260914.csv
```

## Sign-in and payments (manual, outside ARM)

- **Entra External ID**: create an external tenant, register an API app (expose an
  `access_as_user` scope) and a single-page app (redirect URI = the web URL), add Google, Facebook
  and Microsoft identity providers to a sign-up/sign-in user flow, then set the `ENTRA_*` and
  `NEXT_PUBLIC_ENTRA_*` values and redeploy.
- **Stripe** (TODO): create a Pro product with monthly and annual prices, point a webhook at
  `<apiUrl>/webhooks/stripe` for `customer.subscription.created|updated|deleted`, and set the keys
  and prices. Use test mode until the data licensing is settled.

A later multi-cloud setup (AWS/GCP) is expected to use Terraform for the Databricks layer; the
Azure resources here stay in Bicep.
