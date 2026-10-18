param location string
param tags object
param workload string
param environment string
param managedResourceGroupName string

// Premium gives Unity Catalog and serverless jobs. Every new workspace is attached to the
// regional Unity Catalog metastore and gets a catalog named after the workspace, stored in the
// Databricks-managed storage account, which is what the pipeline uses.
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

output workspaceUrl string = workspace.properties.workspaceUrl
output workspaceName string = workspace.name
output workspaceId string = workspace.id
output catalogName string = replace(workspace.name, '-', '_')
