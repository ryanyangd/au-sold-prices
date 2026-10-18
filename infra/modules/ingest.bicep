param location string
param tags object
param workload string
param environment string
param suffix string
param hostStorageName string
param lakeStorageName string
param appInsightsConnectionString string
param sourceUrl string
param ingestSchedule string

var functionName = 'func-${workload}-ingest-${environment}-${suffix}'

resource host 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: hostStorageName
}

resource lake 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: lakeStorageName
}

resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: 'plan-${workload}-ingest-${environment}'
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}

resource app 'Microsoft.Web/sites@2024-04-01' = {
  name: functionName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${host.properties.primaryEndpoints.blob}deploy-pkgs'
          authentication: { type: 'SystemAssignedIdentity' }
        }
      }
      runtime: { name: 'python', version: '3.11' }
      scaleAndConcurrency: {
        maximumInstanceCount: 2
        instanceMemoryMB: 2048
      }
    }
    siteConfig: {
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'AzureWebJobsStorage__accountName', value: host.name }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'LAKE_ACCOUNT_URL', value: lake.properties.primaryEndpoints.blob }
        { name: 'RAW_CONTAINER', value: 'raw' }
        { name: 'SOURCE_URL', value: sourceUrl }
        { name: 'INGEST_SCHEDULE', value: ingestSchedule }
      ]
    }
  }
}

var roles = {
  blobOwner: 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
  blobContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  queueContributor: '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  tableContributor: '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
}

resource hostBlobOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(host.id, app.id, roles.blobOwner)
  scope: host
  properties: {
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.blobOwner)
  }
}

resource hostQueue 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(host.id, app.id, roles.queueContributor)
  scope: host
  properties: {
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.queueContributor)
  }
}

resource hostTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(host.id, app.id, roles.tableContributor)
  scope: host
  properties: {
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.tableContributor)
  }
}

resource lakeWriter 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(lake.id, app.id, roles.blobContributor)
  scope: lake
  properties: {
    principalId: app.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roles.blobContributor)
  }
}

output functionAppName string = app.name
output principalId string = app.identity.principalId
