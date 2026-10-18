# Infrastructure (Bicep)

The normal way to deploy is the GitHub Actions workflow; see [docs/deployment.md](../docs/deployment.md).
This file describes the Bicep itself and the manual commands. One parameter file serves both
environments: set `AUSOLD_ENVIRONMENT=dev|prod` (default `dev`).

Deploys the ingestion and lakehouse foundation into one subscription:

| Resource | Purpose |
|---|---|
| Resource group `rg-<workload>-<env>-aue` | Everything below |
| ADLS Gen2 lake storage | `raw` (downloaded files) and `lakehouse` (Unity Catalog root) containers |
| Function host storage | Deployment packages and trigger state, identity-based auth only |
| Function App (Flex Consumption, Python 3.11) | Daily timer that copies the source archive into `raw/` |
| Databricks workspace (premium) + access connector | Lakehouse compute; the connector reaches the lake through Unity Catalog |
| Log Analytics, Application Insights, alert rule, action group | Monitoring and failure/stale-data alerts |
| Budget | Email alerts at 50/80/100% actual and 100% forecast (does not stop spend) |
| Key Vault (RBAC) | Database URL and Stripe secrets; read by the apps' managed identity |
| PostgreSQL Flexible Server 16 (Burstable) | Serving database (`serving` schema from the pipeline, `app` schema for users/subscriptions); `pg_trgm` allow-listed |
| Container Registry, Container Apps environment, `api` and `web` apps | The FastAPI service and Next.js frontend; secrets come from Key Vault references |

Set `deployApp=false` to deploy only ingestion and the lakehouse.

No keys are stored in code: the Function, Databricks and the apps use managed identities, and
shared-key access is disabled on both storage accounts. Secrets are passed through environment
variables when deploying (see `main.bicepparam`) and land in Key Vault.

Known v1 shortcuts to revisit before real customers: Postgres allows Azure services through
its firewall (no private networking), the API connects with the admin login (create a
least-privilege role and set `grant_select_to` for the pipeline), and there is no Front Door/WAF
or custom domain yet.

## Deploy to a (new) subscription

```sh
az login
az account set --subscription <subscription-id>
export AUSOLD_ALERT_EMAIL=you@example.com
export AUSOLD_PG_PASSWORD="$(openssl rand -base64 24)"   # keep it; it is also stored in Key Vault
# Optional: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_MONTHLY, STRIPE_PRICE_ANNUAL,
# ENTRA_TENANT_ID, ENTRA_TENANT_SUBDOMAIN, ENTRA_API_AUDIENCE (see "Sign-in and payments" below)

az deployment sub what-if -l australiaeast -f infra/main.bicep -p infra/main.bicepparam
az deployment sub create  -l australiaeast -f infra/main.bicep -p infra/main.bicepparam
```

The subscription needs the `Microsoft.Databricks`, `Microsoft.Web`, `Microsoft.Storage`,
`Microsoft.Insights`, `Microsoft.OperationalInsights`, `Microsoft.Consumption`,
`Microsoft.KeyVault`, `Microsoft.DBforPostgreSQL`, `Microsoft.ContainerRegistry`,
`Microsoft.App` and `Microsoft.ManagedIdentity` resource providers registered. Set
`budgetStartDate` to the first day of the current month for a new deployment. Use `extraTags`
or a second parameter file for `prod`.

## Build and deploy the app images

The first deployment runs a placeholder image. Then:

```sh
REG=<registryName output>
az acr build -r $REG -t ausold-api:latest -f docker/api.Dockerfile .
# NEXT_PUBLIC_* values are compiled into the web build; see apps/web/README.md for build args.
az acr build -r $REG -t ausold-web:latest apps/web

az containerapp update -g rg-ausold-dev-aue -n <apiName output> --image $REG.azurecr.io/ausold-api:latest
az containerapp update -g rg-ausold-dev-aue -n <webName output> --image $REG.azurecr.io/ausold-web:latest
```

## Sign-in and payments (manual, outside ARM)

- **Entra External ID**: create an external tenant, register an API app (expose an
  `access_as_user` scope) and a SPA app (redirect URI = the web URL), add Google, Facebook and
  Microsoft identity providers to a sign-up/sign-in user flow, then pass the tenant ID,
  subdomain and API audience to the deployment and the web build.
- **Stripe**: create a Pro product with monthly and annual prices, point a webhook at
  `<apiUrl>/webhooks/stripe` for `customer.subscription.created|updated|deleted`, and pass the
  keys/prices to the deployment. Use test mode until the data licensing is settled.

## Load data into the serving database

From the Databricks pipeline (`load_serving` task) once Databricks can reach Postgres, or for a
first load from your machine (add your IP to the Postgres firewall first):

```sh
export DATABASE_URL="$(az keyvault secret show --vault-name <keyVaultName> -n database-admin-url --query value -o tsv)"
ausold load-postgres --db data/lake.duckdb
```

## Deploy the ingest function

```sh
cd functions/ingest
func azure functionapp publish <ingestFunctionName output> --python
```

Trigger it once to test (Portal: Function App > `ingest_nsw_sales` > Test/Run), then check that
`raw/nsw_psi/<YYYYMMDD>/` holds `archive.zip`, `data.csv` and `_manifest.json`.

## One-time Databricks setup (not in Bicep)

Unity Catalog objects live in the Databricks account/workspace, not in ARM:

1. Confirm the workspace is attached to a Unity Catalog metastore for the region
   (create one in the account console if this is the first workspace there).
2. Create a storage credential from the access connector (`databricksAccessConnectorId` output).
3. Create an external location for `abfss://lakehouse@<lake>.dfs.core.windows.net/` and one for
   `abfss://raw@<lake>.dfs.core.windows.net/`, then `CREATE CATALOG ausold`.
4. Deploy the bronze job with Databricks Asset Bundles from `pipelines/databricks`.

A later multi-cloud setup (AWS/GCP) is expected to move steps 1-3 to Terraform; the Azure
resources here stay in Bicep.
