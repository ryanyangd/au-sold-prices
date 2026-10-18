param location string
param tags object
param workload string
param environment string
param managedResourceGroupName string
param lakeStorageName string

// Premium is required for Unity Catalog and the governance features in the design.
resource workspace 'Microsoft.Databricks/workspaces@2024-05-01' = {
  name: 'dbw-${workload}-${environment}'
  location: location
  tags: tags
  sku: { name: 'premium' }
  properties: {
    managedResourceGroupId: subscriptionResourceId('Microsoft.Resources/resourceGroups', managedResourceGroupName)
    publicNetworkAccess: 'Enabled'
    requiredNsgRules: 'AllRules'
  }
}

// Managed identity Unity Catalog uses to reach the lake (create the storage credential from this).
resource connector 'Microsoft.Databricks/accessConnectors@2024-05-01' = {
  name: 'dbac-${workload}-${environment}'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
}

resource lake 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: lakeStorageName
}

var storageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource connectorOnLake 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(lake.id, connector.id, storageBlobDataContributor)
  scope: lake
  properties: {
    principalId: connector.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributor)
  }
}

output workspaceUrl string = workspace.properties.workspaceUrl
output workspaceName string = workspace.name
output workspaceId string = workspace.id
output accessConnectorId string = connector.id
