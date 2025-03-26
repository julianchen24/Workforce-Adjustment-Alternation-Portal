#!/bin/bash
# Azure Deployment Script for WAAP
# This script automates the deployment of the WAAP application to Azure

# Exit on error
set -e

# Configuration - Replace these values with your own
SUBSCRIPTION_ID="YOUR_SUBSCRIPTION_ID"
RESOURCE_GROUP="waap-resource-group"
LOCATION="eastus"
POSTGRES_SERVER_NAME="waap-postgres"
POSTGRES_ADMIN_USER="waap_admin"
POSTGRES_ADMIN_PASSWORD="YOUR_SECURE_PASSWORD"
DB_NAME="waap_db"
STORAGE_ACCOUNT_NAME="waapstatic"
APP_SERVICE_PLAN="waap-app-service-plan"
WEB_APP_NAME="waap-app"
INSIGHTS_NAME="waap-insights"

# Django settings
DJANGO_SECRET_KEY="YOUR_SECURE_SECRET_KEY"
RECAPTCHA_PUBLIC_KEY="YOUR_RECAPTCHA_PUBLIC_KEY"
RECAPTCHA_PRIVATE_KEY="YOUR_RECAPTCHA_PRIVATE_KEY"
EMAIL_HOST="YOUR_EMAIL_HOST"
EMAIL_PORT="587"
EMAIL_HOST_USER="YOUR_EMAIL_USER"
EMAIL_HOST_PASSWORD="YOUR_EMAIL_PASSWORD"
DEFAULT_FROM_EMAIL="noreply@yourdomain.com"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display status messages
function echo_status {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Function to display warning messages
function echo_warning {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to display error messages
function echo_error {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo_error "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in to Azure
az account show &> /dev/null || {
    echo_warning "Not logged in to Azure. Please log in."
    az login
}

# Set the subscription
echo_status "Setting subscription to $SUBSCRIPTION_ID"
az account set --subscription "$SUBSCRIPTION_ID"

# Create resource group if it doesn't exist
echo_status "Creating resource group $RESOURCE_GROUP in $LOCATION"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none || true

# Create PostgreSQL server
echo_status "Creating PostgreSQL server $POSTGRES_SERVER_NAME"
az postgres server create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$POSTGRES_SERVER_NAME" \
    --location "$LOCATION" \
    --admin-user "$POSTGRES_ADMIN_USER" \
    --admin-password "$POSTGRES_ADMIN_PASSWORD" \
    --sku-name GP_Gen5_2 \
    --version 12 \
    --output none || echo_warning "PostgreSQL server already exists or could not be created"

# Configure firewall rules to allow Azure services
echo_status "Configuring PostgreSQL firewall rules"
az postgres server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --server "$POSTGRES_SERVER_NAME" \
    --name AllowAllAzureIPs \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    --output none || echo_warning "Firewall rule already exists or could not be created"

# Create database
echo_status "Creating database $DB_NAME"
az postgres db create \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER_NAME" \
    --name "$DB_NAME" \
    --output none || echo_warning "Database already exists or could not be created"

# Create storage account for static files
echo_status "Creating storage account $STORAGE_ACCOUNT_NAME"
az storage account create \
    --name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --output none || echo_warning "Storage account already exists or could not be created"

# Get storage account key
echo_status "Getting storage account key"
STORAGE_ACCOUNT_KEY=$(az storage account keys list \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[0].value" \
    --output tsv)

# Create container for static files
echo_status "Creating storage container for static files"
az storage container create \
    --name static \
    --account-name "$STORAGE_ACCOUNT_NAME" \
    --account-key "$STORAGE_ACCOUNT_KEY" \
    --public-access blob \
    --output none || echo_warning "Container already exists or could not be created"

# Create App Service Plan
echo_status "Creating App Service Plan $APP_SERVICE_PLAN"
az appservice plan create \
    --name "$APP_SERVICE_PLAN" \
    --resource-group "$RESOURCE_GROUP" \
    --sku B1 \
    --is-linux \
    --output none || echo_warning "App Service Plan already exists or could not be created"

# Create Web App
echo_status "Creating Web App $WEB_APP_NAME"
az webapp create \
    --resource-group "$RESOURCE_GROUP" \
    --plan "$APP_SERVICE_PLAN" \
    --name "$WEB_APP_NAME" \
    --runtime "PYTHON|3.12" \
    --deployment-local-git \
    --output none || echo_warning "Web App already exists or could not be created"

# Configure environment variables
echo_status "Configuring environment variables"
az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --settings \
    DJANGO_SETTINGS_MODULE=waap_project.settings_production \
    DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
    ALLOWED_HOSTS="$WEB_APP_NAME.azurewebsites.net,yourdomain.com" \
    DB_NAME="$DB_NAME" \
    DB_USER="$POSTGRES_ADMIN_USER@$POSTGRES_SERVER_NAME" \
    DB_PASSWORD="$POSTGRES_ADMIN_PASSWORD" \
    DB_HOST="$POSTGRES_SERVER_NAME.postgres.database.azure.com" \
    DB_PORT=5432 \
    RECAPTCHA_PUBLIC_KEY="$RECAPTCHA_PUBLIC_KEY" \
    RECAPTCHA_PRIVATE_KEY="$RECAPTCHA_PRIVATE_KEY" \
    EMAIL_HOST="$EMAIL_HOST" \
    EMAIL_PORT="$EMAIL_PORT" \
    EMAIL_USE_TLS=True \
    EMAIL_HOST_USER="$EMAIL_HOST_USER" \
    EMAIL_HOST_PASSWORD="$EMAIL_HOST_PASSWORD" \
    DEFAULT_FROM_EMAIL="$DEFAULT_FROM_EMAIL" \
    LOG_FILE=/home/LogFiles/waap.log \
    AZURE_STORAGE_ACCOUNT_NAME="$STORAGE_ACCOUNT_NAME" \
    AZURE_STORAGE_ACCOUNT_KEY="$STORAGE_ACCOUNT_KEY" \
    AZURE_STORAGE_CONTAINER=static \
    --output none

# Create Application Insights
echo_status "Creating Application Insights $INSIGHTS_NAME"
az monitor app-insights component create \
    --app "$INSIGHTS_NAME" \
    --location "$LOCATION" \
    --resource-group "$RESOURCE_GROUP" \
    --output none || echo_warning "Application Insights already exists or could not be created"

# Link Application Insights to the Web App
echo_status "Linking Application Insights to Web App"
APPINSIGHTS_KEY=$(az monitor app-insights component show \
    --app "$INSIGHTS_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query instrumentationKey \
    --output tsv)

az webapp config appsettings set \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --settings APPINSIGHTS_INSTRUMENTATIONKEY="$APPINSIGHTS_KEY" \
    --output none

# Prepare WebJob for auto-expiration
echo_status "Preparing WebJob for auto-expiration"
mkdir -p webjob_temp
cat > webjob_temp/expire_job_postings.sh << EOF
#!/bin/bash
cd \$WEBROOT_PATH
python manage.py expire_job_postings --settings=waap_project.settings_production
EOF

cat > webjob_temp/settings.job << EOF
{
  "schedule": "0 0 * * *"
}
EOF

# Create a zip file for the WebJob
cd webjob_temp
zip -r expire_job_postings.zip .
cd ..

# Upload the WebJob
echo_status "Uploading WebJob for auto-expiration"
az webapp webjob upload \
    --resource-group "$RESOURCE_GROUP" \
    --name "$WEB_APP_NAME" \
    --webjob-name expire-job-postings \
    --webjob-type triggered \
    --src webjob_temp/expire_job_postings.zip \
    --output none || echo_warning "WebJob could not be uploaded"

# Clean up temporary files
rm -rf webjob_temp

echo_status "Deployment configuration complete!"
echo_status "Next steps:"
echo_status "1. Update your local git repository to include the required files (web.config, runserver.py)"
echo_status "2. Deploy your code with: git push azure main"
echo_status "3. Run migrations and collect static files"
echo_status "4. Test your application at https://$WEB_APP_NAME.azurewebsites.net"
