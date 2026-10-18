param lakeStorageName string

@description('Object ID of a person who uploads/inspects lake data (optional).')
param adminObjectId string = ''

@description('Object ID of the CI/CD service principal that checks ingest results (optional).')
param deployerObjectId string = ''

resource lake 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: lakeStorageName
}

var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource adminOnLake 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(adminObjectId)) {
  name: guid(lake.id, adminObjectId, storageBlobDataContributor)
  scope: lake
  properties: {
    principalId: adminObjectId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
  }
}

resource deployerOnLake 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(lake.id, deployerObjectId, storageBlobDataContributor)
  scope: lake
  properties: {
    principalId: deployerObjectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
  }
}
