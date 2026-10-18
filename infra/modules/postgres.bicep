param location string
param tags object
param workload string
param environment string
param suffix string
@description('Administrator login for the server (used by the data load; the API gets its own role).')
param adminLogin string = 'ausoldadmin'

@secure()
param adminPassword string

param databaseName string = 'ausold'
param skuName string = 'Standard_B2s'
param tier string = 'Burstable'
param storageSizeGB int = 64
param backupRetentionDays int = 7

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: 'psql-${workload}-${environment}-${suffix}'
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: tier
  }
  properties: {
    version: '16'
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    storage: { storageSizeGB: storageSizeGB }
    backup: { backupRetentionDays: backupRetentionDays, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    authConfig: { activeDirectoryAuth: 'Disabled', passwordAuth: 'Enabled' }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: server
  name: databaseName
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource extensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'azure.extensions'
  properties: { value: 'PG_TRGM', source: 'user-override' }
  dependsOn: [database] // the server rejects concurrent child-resource writes
}

// v1: reachable from Azure services (Container Apps, Databricks) and TLS-only. Move to
// private networking before real customer data or payments go live.
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: server
  name: 'AllowAzureServices'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
  dependsOn: [extensions]
}

var host = server.properties.fullyQualifiedDomainName

output serverName string = server.name
output host string = host
output databaseName string = databaseName
