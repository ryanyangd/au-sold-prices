using 'main.bicep'

// One parameter file for every environment. The environment name comes from AUSOLD_ENVIRONMENT
// (dev|prod) and everything else from environment variables set by the deploy workflow or by
// you. Secrets are never stored in this file.
var env = readEnvironmentVariable('AUSOLD_ENVIRONMENT', 'dev')

param environment = env
param location = readEnvironmentVariable('AUSOLD_LOCATION', 'australiaeast')
param alertEmail = readEnvironmentVariable('AUSOLD_ALERT_EMAIL', 'owner@example.com')

// Total budget target is A$2,000 a month: A$600 dev, A$1,400 prod. Alerts only.
param monthlyBudgetAud = env == 'prod' ? 1400 : 600
param budgetStartDate = readEnvironmentVariable('AUSOLD_BUDGET_START', '2026-10-01')

param postgresAdminPassword = readEnvironmentVariable('AUSOLD_PG_PASSWORD', '')
param stripeSecretKey = readEnvironmentVariable('STRIPE_SECRET_KEY', '')
param stripeWebhookSecret = readEnvironmentVariable('STRIPE_WEBHOOK_SECRET', '')
param stripePriceMonthly = readEnvironmentVariable('STRIPE_PRICE_MONTHLY', '')
param stripePriceAnnual = readEnvironmentVariable('STRIPE_PRICE_ANNUAL', '')

param entraTenantId = readEnvironmentVariable('ENTRA_TENANT_ID', '')
param entraTenantSubdomain = readEnvironmentVariable('ENTRA_TENANT_SUBDOMAIN', '')
param entraApiAudience = readEnvironmentVariable('ENTRA_API_AUDIENCE', '')
param appBaseUrl = readEnvironmentVariable('AUSOLD_APP_BASE_URL', '')

// The deploy workflow sets these to the images already running so infra runs don't reset them.
param apiImage = readEnvironmentVariable('AUSOLD_API_IMAGE', 'mcr.microsoft.com/k8se/quickstart:latest')
param webImage = readEnvironmentVariable('AUSOLD_WEB_IMAGE', 'mcr.microsoft.com/k8se/quickstart:latest')
