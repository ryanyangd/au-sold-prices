// Subscription-scope entry point. Deploys the ingestion + lakehouse foundation:
// monitoring, ADLS Gen2 lake, Databricks workspace, ingest Function and a budget.
targetScope = 'subscription'

@description('Environment name, used in resource names.')
@allowed(['dev', 'prod'])
param environment string = 'dev'

@description('Azure region for every resource.')
param location string = 'australiaeast'

@description('Short workload name used as a resource name prefix.')
@minLength(3)
@maxLength(8)
param workload string = 'ausold'

@description('Email that receives budget and failure alerts.')
param alertEmail string

@description('Monthly budget in AUD for this workload (alerts only, does not stop spend).')
param monthlyBudgetAud int = 2000

@description('First day of the budget period (budgets must start on the 1st of a month).')
param budgetStartDate string = '2026-10-01'

@description('Archive the ingest function downloads.')
param sourceUrl string = 'https://nswpropertysalesdata.com/data/archive.zip'

@description('CRON (UTC) for the daily ingest. Default is 18:00 UTC, about 05:00 in Sydney (before the 07:00 pipeline).')
param ingestSchedule string = '0 0 18 * * *'

@description('Extra tags applied to every resource.')
param extraTags object = {}

@description('Also deploy the web/API/database tier. Set false for ingestion + lakehouse only.')
param deployApp bool = true

@secure()
@description('Postgres admin password (required when deployApp is true; 16+ chars).')
param postgresAdminPassword string = ''

@secure()
param stripeSecretKey string = ''

@secure()
param stripeWebhookSecret string = ''

param stripePriceMonthly string = ''
param stripePriceAnnual string = ''

@description('Object ID of a user allowed to manage Key Vault secrets (optional).')
param adminObjectId string = ''

@description('Microsoft Entra External ID tenant used for customer sign-in (created separately).')
param entraTenantId string = ''
param entraTenantSubdomain string = ''
param entraApiAudience string = ''

@description('Public URL of the web app if using a custom domain; empty uses the default URL.')
param appBaseUrl string = ''

param apiImage string = 'mcr.microsoft.com/k8se/quickstart:latest'
param webImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Object ID of the CI/CD service principal (GitHub OIDC). Gets read access to secrets and the lake.')
param deployerObjectId string = ''

@description('Postgres compute. Dev: Burstable. Prod: GeneralPurpose.')
param postgresSku string = environment == 'prod' ? 'Standard_D2ds_v5' : 'Standard_B2s'
param postgresTier string = environment == 'prod' ? 'GeneralPurpose' : 'Burstable'
param postgresStorageGB int = environment == 'prod' ? 128 : 64
param postgresBackupDays int = environment == 'prod' ? 14 : 7

@description('Minimum API/web replicas. Prod keeps two for availability.')
param minReplicas int = environment == 'prod' ? 2 : 1

var tags = union({
  workload: workload
  environment: environment
  managedBy: 'bicep'
}, extraTags)

var rgName = 'rg-${workload}-${environment}-aue'
var suffix = take(uniqueString(subscription().subscriptionId, rgName), 6)
var databricksManagedRgName = 'rg-${workload}-${environment}-dbx-managed'

// Prod always requires real sign-in. Non-prod uses a dev login until Entra is configured.
var authMode = (environment == 'prod' || !empty(entraTenantId)) ? 'entra' : 'dev'

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: tags
}

module monitoring 'modules/monitoring.bicep' = {
  scope: rg
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    alertEmail: alertEmail
  }
}

module storage 'modules/storage.bicep' = {
  scope: rg
  name: 'storage'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
  }
}

module databricks 'modules/databricks.bicep' = {
  scope: rg
  name: 'databricks'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    managedResourceGroupName: databricksManagedRgName
    lakeStorageName: storage.outputs.lakeStorageName
  }
}

module ingest 'modules/ingest.bicep' = {
  scope: rg
  name: 'ingest'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
    hostStorageName: storage.outputs.hostStorageName
    lakeStorageName: storage.outputs.lakeStorageName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    sourceUrl: sourceUrl
    ingestSchedule: ingestSchedule
  }
}

module keyvault 'modules/keyvault.bicep' = if (deployApp) {
  scope: rg
  name: 'keyvault'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
    adminObjectId: adminObjectId
    deployerObjectId: deployerObjectId
  }
}

module access 'modules/access.bicep' = {
  scope: rg
  name: 'access'
  params: {
    lakeStorageName: storage.outputs.lakeStorageName
    adminObjectId: adminObjectId
    deployerObjectId: deployerObjectId
  }
}

module postgres 'modules/postgres.bicep' = if (deployApp) {
  scope: rg
  name: 'postgres'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
    keyVaultName: keyvault!.outputs.name
    adminPassword: postgresAdminPassword
    skuName: postgresSku
    tier: postgresTier
    storageSizeGB: postgresStorageGB
    backupRetentionDays: postgresBackupDays
  }
}

module secrets 'modules/secrets.bicep' = if (deployApp) {
  scope: rg
  name: 'secrets'
  params: {
    keyVaultName: keyvault!.outputs.name
    stripeSecretKey: stripeSecretKey
    stripeWebhookSecret: stripeWebhookSecret
  }
}

module apps 'modules/apps.bicep' = if (deployApp) {
  scope: rg
  name: 'apps'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
    databaseUrl: 'postgresql://ausoldadmin:${uriComponent(postgresAdminPassword)}@${postgres!.outputs.host}:5432/${postgres!.outputs.databaseName}?sslmode=require'
    stripeSecretKey: stripeSecretKey
    stripeWebhookSecret: stripeWebhookSecret
    logAnalyticsId: monitoring.outputs.logAnalyticsId
    apiImage: apiImage
    webImage: webImage
    entraTenantId: entraTenantId
    entraTenantSubdomain: entraTenantSubdomain
    entraApiAudience: entraApiAudience
    authMode: authMode
    minReplicas: minReplicas
    stripePriceMonthly: stripePriceMonthly
    stripePriceAnnual: stripePriceAnnual
    appBaseUrl: appBaseUrl
  }
  dependsOn: [postgres, secrets]
}

module budget 'modules/budget.bicep' = {
  name: 'budget'
  params: {
    name: 'budget-${workload}-${environment}'
    amount: monthlyBudgetAud
    startDate: budgetStartDate
    resourceGroupNames: [rgName, databricksManagedRgName]
    contactEmails: [alertEmail]
  }
}

output resourceGroupName string = rg.name
output lakeStorageName string = storage.outputs.lakeStorageName
output ingestFunctionName string = ingest.outputs.functionAppName
output databricksWorkspaceUrl string = databricks.outputs.workspaceUrl
output databricksAccessConnectorId string = databricks.outputs.accessConnectorId
output databricksWorkspaceName string = databricks.outputs.workspaceName
output authMode string = authMode
output keyVaultName string = deployApp ? keyvault!.outputs.name : ''
output postgresHost string = deployApp ? postgres!.outputs.host : ''
output registryName string = deployApp ? apps!.outputs.registryName : ''
output apiName string = deployApp ? apps!.outputs.apiName : ''
output apiUrl string = deployApp ? apps!.outputs.apiUrl : ''
output webName string = deployApp ? apps!.outputs.webName : ''
output webUrl string = deployApp ? apps!.outputs.webUrl : ''
