param location string
param tags object
param workload string
param environment string
param alertEmail string

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${workload}-${environment}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${workload}-${environment}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
  }
}

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-${workload}-${environment}'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: take('${workload}${environment}', 12)
    enabled: true
    emailReceivers: [
      {
        name: 'owner'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

// Fires when the ingest function logs an exception or a stale-data warning.
resource ingestAlert 'Microsoft.Insights/scheduledQueryRules@2022-06-15' = {
  name: 'alert-${workload}-${environment}-ingest-problem'
  location: location
  tags: tags
  properties: {
    displayName: 'Ingest function failed or data is stale'
    severity: 2
    enabled: true
    scopes: [appInsights.id]
    evaluationFrequency: 'PT1H'
    windowSize: 'P1D'
    criteria: {
      allOf: [
        {
          query: '''
            union
              (exceptions | where cloud_RoleName startswith "func-"),
              (traces | where cloud_RoleName startswith "func-" and (severityLevel >= 3 or message has "STALE_SOURCE"))
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [actionGroup.id]
    }
  }
}

output appInsightsConnectionString string = appInsights.properties.ConnectionString
output logAnalyticsId string = logs.id
