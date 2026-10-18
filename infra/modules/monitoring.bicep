param location string
param tags object
param workload string
param environment string

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${workload}-${environment}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

output logAnalyticsId string = logs.id
