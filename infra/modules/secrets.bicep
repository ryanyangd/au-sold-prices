param keyVaultName string

@secure()
param stripeSecretKey string = ''

@secure()
param stripeWebhookSecret string = ''

// Empty values are stored as 'not-set'; the API treats that as "billing not configured".
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource stripeKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'stripe-secret-key'
  properties: { value: empty(stripeSecretKey) ? 'not-set' : stripeSecretKey }
}

resource stripeWebhook 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'stripe-webhook-secret'
  properties: { value: empty(stripeWebhookSecret) ? 'not-set' : stripeWebhookSecret }
}
