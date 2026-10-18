param location string
param tags object
param workload string
param environment string
param suffix string

var lakeName = toLower('st${workload}${environment}lake${suffix}')
var hostName = toLower('st${workload}${environment}fn${suffix}')

// ADLS Gen2 lake: `raw` receives downloaded files, `lakehouse` is the Unity Catalog storage root.
resource lake 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: lakeName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    isHnsEnabled: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    defaultToOAuthAuthentication: true
  }
}

resource lakeBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: lake
  name: 'default'
  properties: {
    deleteRetentionPolicy: { enabled: true, days: 7 }
    containerDeleteRetentionPolicy: { enabled: true, days: 7 }
  }
}

resource rawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: lakeBlob
  name: 'raw'
}

resource lakehouseContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: lakeBlob
  name: 'lakehouse'
}

resource lakeLifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: lake
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'raw-to-cool'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: { blobTypes: ['blockBlob'], prefixMatch: ['raw/'] }
            actions: {
              baseBlob: { tierToCool: { daysAfterModificationGreaterThan: 30 } }
            }
          }
        }
      ]
    }
  }
}

// Function host storage: deployment packages and trigger state (identity-based auth only).
resource host 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: hostName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    defaultToOAuthAuthentication: true
  }
}

resource hostBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: host
  name: 'default'
}

resource deployContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: hostBlob
  name: 'deploy-pkgs'
}

output lakeStorageName string = lake.name
output hostStorageName string = host.name
