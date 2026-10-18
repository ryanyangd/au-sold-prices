param location string
param tags object
param workload string
param environment string
param suffix string
@secure()
param databaseUrl string

@secure()
param stripeSecretKey string = ''

@secure()
param stripeWebhookSecret string = ''
param logAnalyticsId string

@description('Initial images. Replace via `az containerapp update` once the real images are pushed.')
param apiImage string = 'mcr.microsoft.com/k8se/quickstart:latest'
param webImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

param entraTenantId string = ''
param entraTenantSubdomain string = ''
param entraApiAudience string = ''

@allowed(['entra', 'dev'])
param authMode string = 'entra'
param minReplicas int = 1
param stripePriceMonthly string = ''
param stripePriceAnnual string = ''

@description('Public URL of the web app, used for CORS and Stripe redirects. Empty = the default Container Apps URL.')
param appBaseUrl string = ''

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: last(split(logAnalyticsId, '/'))
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cr${workload}${environment}${suffix}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${workload}-apps-${environment}'
  location: location
  tags: tags
}

var acrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, acrPull)
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPull)
  }
}

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${workload}-${environment}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// The first deployment runs a placeholder image on port 80 without probes; real images use
// the app ports and health probes.
var apiPlaceholder = startsWith(apiImage, 'mcr.microsoft.com/')
var webPlaceholder = startsWith(webImage, 'mcr.microsoft.com/')
var apiPort = apiPlaceholder ? 80 : 8000
var webPort = webPlaceholder ? 80 : 3000

var webName = 'ca-${workload}-web-${environment}'
var apiName = 'ca-${workload}-api-${environment}'
var envDomain = env.properties.defaultDomain
var webUrl = empty(appBaseUrl) ? 'https://${webName}.${envDomain}' : appBaseUrl

// Key Vault has public network access disabled by policy in some tenants, so Container Apps
// cannot reference it; the values are passed in as secure parameters and kept as app secrets.
var appSecrets = [
  { name: 'database-url', value: databaseUrl }
  { name: 'stripe-secret-key', value: empty(stripeSecretKey) ? 'not-set' : stripeSecretKey }
  { name: 'stripe-webhook-secret', value: empty(stripeWebhookSecret) ? 'not-set' : stripeWebhookSecret }
]

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: apiName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: apiPort, transport: 'auto' }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
      secrets: appSecrets
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'ENVIRONMENT', value: environment }
            { name: 'AUTH_MODE', value: authMode }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'STRIPE_SECRET_KEY', secretRef: 'stripe-secret-key' }
            { name: 'STRIPE_WEBHOOK_SECRET', secretRef: 'stripe-webhook-secret' }
            { name: 'STRIPE_PRICE_MONTHLY', value: stripePriceMonthly }
            { name: 'STRIPE_PRICE_ANNUAL', value: stripePriceAnnual }
            { name: 'ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'ENTRA_TENANT_SUBDOMAIN', value: entraTenantSubdomain }
            { name: 'ENTRA_API_AUDIENCE', value: entraApiAudience }
            { name: 'APP_BASE_URL', value: webUrl }
            { name: 'CORS_ORIGINS', value: webUrl }
          ]
          probes: apiPlaceholder ? [] : [
            { type: 'Liveness', httpGet: { path: '/health', port: 8000 } }
            // Not /health/ready: a database outage must not remove the API from rotation, or every
            // request would hang instead of failing fast with 503.
            { type: 'Readiness', httpGet: { path: '/health', port: 8000 } }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: 3
        rules: [{ name: 'http', http: { metadata: { concurrentRequests: '50' } } }]
      }
    }
  }
  dependsOn: [pullRole]
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: webName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: webPort, transport: 'auto' }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          probes: webPlaceholder ? [] : [{ type: 'Liveness', httpGet: { path: '/', port: 3000 } }]
        }
      ]
      scale: { minReplicas: minReplicas, maxReplicas: 3 }
    }
  }
  dependsOn: [pullRole]
}

output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output apiName string = api.name
output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output webName string = web.name
output webUrl string = 'https://${web.properties.configuration.ingress.fqdn}'
output identityPrincipalId string = identity.properties.principalId
