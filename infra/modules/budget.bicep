targetScope = 'subscription'

param name string
param amount int
param startDate string
param resourceGroupNames array
param contactEmails array

var thresholds = [
  { key: 'actual50', threshold: 50, type: 'Actual' }
  { key: 'actual80', threshold: 80, type: 'Actual' }
  { key: 'actual100', threshold: 100, type: 'Actual' }
  { key: 'forecast100', threshold: 100, type: 'Forecasted' }
]

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: { startDate: startDate }
    filter: {
      dimensions: {
        name: 'ResourceGroupName'
        operator: 'In'
        values: resourceGroupNames
      }
    }
    notifications: toObject(thresholds, t => t.key, t => {
      enabled: true
      operator: 'GreaterThan'
      threshold: t.threshold
      thresholdType: t.type
      contactEmails: contactEmails
    })
  }
}
