// Subscription-scope entry point for one environment (dev or prod): Databricks workspace,
// PostgreSQL, the API and web Container Apps, monitoring and a budget.
//
// The data pipeline runs entirely inside Databricks (ingest -> bronze -> silver -> gold -> Postgres)
// on Databricks-managed storage, so there is no customer storage account. This keeps the design
// working in subscriptions whose policy forces storage and Key Vault public access off.
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

@description('Email that receives budget alerts.')
param alertEmail string

@description('Monthly budget in AUD for this workload (alerts only, does not stop spend).')
param monthlyBudgetAud int = 2000

@description('First day of the budget period (budgets must start on the 1st of a month).')
param budgetStartDate string = '2026-10-01'

@description('Extra tags applied to every resource.')
param extraTags object = {}

@secure()
@description('Postgres admin password (16+ characters, letters and digits only).')
param postgresAdminPassword string

@secure()
param stripeSecretKey string = ''

@secure()
param stripeWebhookSecret string = ''

param stripePriceMonthly string = ''
param stripePriceAnnual string = ''

@description('Microsoft Entra External ID tenant used for customer sign-in (created separately).')
param entraTenantId string = ''
param entraTenantSubdomain string = ''
param entraApiAudience string = ''

@description('Public URL of the web app if using a custom domain; empty uses the default URL.')
param appBaseUrl string = ''

param apiImage string = 'mcr.microsoft.com/k8se/quickstart:latest'
param webImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

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
  }
}

module postgres 'modules/postgres.bicep' = {
  scope: rg
  name: 'postgres'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
    adminPassword: postgresAdminPassword
    skuName: postgresSku
    tier: postgresTier
    storageSizeGB: postgresStorageGB
    backupRetentionDays: postgresBackupDays
  }
}

module apps 'modules/apps.bicep' = {
  scope: rg
  name: 'apps'
  params: {
    location: location
    tags: tags
    workload: workload
    environment: environment
    suffix: suffix
    databaseUrl: 'postgresql://ausoldadmin:${uriComponent(postgresAdminPassword)}@${postgres.outputs.host}:5432/${postgres.outputs.databaseName}?sslmode=require'
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
output databricksWorkspaceName string = databricks.outputs.workspaceName
output databricksWorkspaceUrl string = databricks.outputs.workspaceUrl
output databricksWorkspaceId string = databricks.outputs.workspaceId
// Azure Databricks creates a catalog named after the workspace (dashes become underscores).
output databricksCatalog string = databricks.outputs.catalogName
output postgresHost string = postgres.outputs.host
output registryName string = apps.outputs.registryName
output apiName string = apps.outputs.apiName
output apiUrl string = apps.outputs.apiUrl
output webName string = apps.outputs.webName
output webUrl string = apps.outputs.webUrl
output authMode string = authMode
