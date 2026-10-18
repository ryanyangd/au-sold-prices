param location string
param tags object
param workload string
param environment string
param suffix string
param tenantId string = tenant().tenantId

@description('Object ID of the identity that deploys and may manage secrets (optional).')
param adminObjectId string = ''

@description('Object ID of the CI/CD service principal; gets read access to secrets (optional).')
param deployerObjectId string = ''

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${workload}-${environment}-${suffix}'
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

var keyVaultSecretsUser = '4633458b-17de-4789-a0b3-9c8e8bf1a5a3'
var keyVaultAdministrator = '00482a5a-887f-4fb3-b363-3b7fe8e74483'

resource deployerRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(vault.id, deployerObjectId, keyVaultSecretsUser)
  scope: vault
  properties: {
    principalId: deployerObjectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUser)
  }
}

resource adminRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(adminObjectId)) {
  name: guid(vault.id, adminObjectId, keyVaultAdministrator)
  scope: vault
  properties: {
    principalId: adminObjectId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultAdministrator)
  }
}

output name string = vault.name
output uri string = vault.properties.vaultUri
