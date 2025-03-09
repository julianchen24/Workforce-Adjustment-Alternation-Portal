# Azure Deployment Guide for WAAP

This guide provides instructions for deploying the WAAP application on Microsoft Azure.

## Prerequisites

- Azure account with appropriate permissions
- Azure CLI installed and configured
- Git installed
- Python 3.12+ installed locally

## Deployment Options

There are several options for deploying the WAAP application on Azure:

1. **Azure App Service**: Simplest option, good for small to medium applications
2. **Azure Kubernetes Service (AKS)**: More control, better for scaling
3. **Azure Virtual Machines**: Full control, more management overhead

This guide focuses on the Azure App Service approach, which is the simplest.

## Deployment Steps

### 1. Prepare the Application

1. Update the requirements.txt file to include all production dependencies:

```bash
pip install gunicorn
pip freeze > requirements.txt
```

2. Create an Azure App Service configuration file `azure.json`:

```json
{
  "appService.defaultWebAppToDeploy": "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/Microsoft.Web/sites/YOUR_APP_NAME",
  "appService.deploySubpath": "."
}
```

3. Create a `web.config` file in the project root:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="httpPlatformHandler" path="*" verb="*" modules="httpPlatformHandler" resourceType="Unspecified" />
    </handlers>
    <httpPlatform processPath="%home%\site\wwwroot\env\Scripts\python.exe" arguments="%home%\site\wwwroot\runserver.py" requestTimeout="00:04:00" startupTimeLimit="120" startupRetryCount="3" stdoutLogEnabled="true" stdoutLogFile="%home%\LogFiles\python.log">
      <environmentVariables>
        <environmentVariable name="PYTHONPATH" value="%home%\site\wwwroot" />
        <environmentVariable name="DJANGO_SETTINGS_MODULE" value="waap_project.settings_production" />
      </environmentVariables>
    </httpPlatform>
  </system.webServer>
</configuration>
```

4. Create a `runserver.py` file in the project root:

```python
import os
from waitress import serve
from waap_project.wsgi import application

serve(application, host="0.0.0.0", port=os.environ.get("PORT", 8000))
```

### 2. Set Up Azure Resources

#### Resource Group

1. Create a resource group:

```bash
az group create --name waap-resource-group --location eastus
```

#### Database (Azure Database for PostgreSQL)

1. Create a PostgreSQL server:

```bash
az postgres server create \
    --resource-group waap-resource-group \
    --name waap-postgres \
    --location eastus \
    --admin-user waap_admin \
    --admin-password YOUR_PASSWORD \
    --sku-name GP_Gen5_2 \
    --version 12
```

2. Configure firewall rules to allow Azure services:

```bash
az postgres server firewall-rule create \
    --resource-group waap-resource-group \
    --server waap-postgres \
    --name AllowAllAzureIPs \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0
```

3. Create a database:

```bash
az postgres db create \
    --resource-group waap-resource-group \
    --server-name waap-postgres \
    --name waap_db
```

#### Storage Account for Static Files

1. Create a storage account:

```bash
az storage account create \
    --name waapstatic \
    --resource-group waap-resource-group \
    --location eastus \
    --sku Standard_LRS
```

2. Create a container for static files:

```bash
az storage container create \
    --name static \
    --account-name waapstatic \
    --public-access blob
```

### 3. Deploy with Azure App Service

1. Create an App Service Plan:

```bash
az appservice plan create \
    --name waap-app-service-plan \
    --resource-group waap-resource-group \
    --sku B1 \
    --is-linux
```

2. Create a Web App:

```bash
az webapp create \
    --resource-group waap-resource-group \
    --plan waap-app-service-plan \
    --name waap-app \
    --runtime "PYTHON|3.12" \
    --deployment-local-git
```

3. Configure environment variables:

```bash
az webapp config appsettings set \
    --resource-group waap-resource-group \
    --name waap-app \
    --settings \
    DJANGO_SETTINGS_MODULE=waap_project.settings_production \
    DJANGO_SECRET_KEY=YOUR_SECRET_KEY_HERE \
    ALLOWED_HOSTS=waap-app.azurewebsites.net,yourdomain.com \
    DB_NAME=waap_db \
    DB_USER=waap_admin@waap-postgres \
    DB_PASSWORD=YOUR_DB_PASSWORD_HERE \
    DB_HOST=waap-postgres.postgres.database.azure.com \
    DB_PORT=5432 \
    RECAPTCHA_PUBLIC_KEY=YOUR_RECAPTCHA_PUBLIC_KEY \
    RECAPTCHA_PRIVATE_KEY=YOUR_RECAPTCHA_PRIVATE_KEY \
    EMAIL_HOST=YOUR_EMAIL_HOST \
    EMAIL_PORT=587 \
    EMAIL_USE_TLS=True \
    EMAIL_HOST_USER=YOUR_EMAIL_USER \
    EMAIL_HOST_PASSWORD=YOUR_EMAIL_PASSWORD \
    DEFAULT_FROM_EMAIL=noreply@yourdomain.com \
    LOG_FILE=/home/LogFiles/waap.log \
    AZURE_STORAGE_ACCOUNT_NAME=waapstatic \
    AZURE_STORAGE_ACCOUNT_KEY=YOUR_STORAGE_ACCOUNT_KEY \
    AZURE_STORAGE_CONTAINER=static
```

4. Deploy the application:

```bash
git remote add azure https://YOUR_DEPLOYMENT_USER@waap-app.scm.azurewebsites.net/waap-app.git
git push azure main
```

5. Run migrations and collect static files:

```bash
az webapp ssh --resource-group waap-resource-group --name waap-app
cd site/wwwroot
python manage.py migrate --settings=waap_project.settings_production
python manage.py collectstatic --settings=waap_project.settings_production
```

### 4. Set Up Auto-Expiration Task with Azure WebJobs

1. Create a WebJob script file `expire_job_postings.sh`:

```bash
#!/bin/bash
cd $WEBROOT_PATH
python manage.py expire_job_postings --settings=waap_project.settings_production
```

2. Create a settings file `settings.job`:

```json
{
  "schedule": "0 0 * * *"
}
```

3. Upload the WebJob:

```bash
az webapp webjob create \
    --resource-group waap-resource-group \
    --name waap-app \
    --webjob-name expire-job-postings \
    --webjob-type triggered \
    --webjob-script-file-path expire_job_postings.sh \
    --webjob-script-file-path settings.job
```

### 5. Set Up Monitoring and Logging

1. Enable Application Insights:

```bash
az monitor app-insights component create \
    --app waap-insights \
    --location eastus \
    --resource-group waap-resource-group
```

2. Link Application Insights to the Web App:

```bash
APPINSIGHTS_KEY=$(az monitor app-insights component show \
    --app waap-insights \
    --resource-group waap-resource-group \
    --query instrumentationKey \
    --output tsv)

az webapp config appsettings set \
    --resource-group waap-resource-group \
    --name waap-app \
    --settings APPINSIGHTS_INSTRUMENTATIONKEY=$APPINSIGHTS_KEY
```

## Automated Deployment Script

You can use the `deploy_azure.sh` script in this directory to automate the deployment process.

## Troubleshooting

- **Application not starting**: Check the App Service logs in the Azure portal
- **Database connection issues**: Verify PostgreSQL server firewall settings
- **Static files not loading**: Check Storage Account permissions and STATICFILES_STORAGE setting
- **Email not sending**: Verify email service configuration and limits

## Security Considerations

- Use Azure Key Vault for storing sensitive credentials
- Enable Azure Application Gateway for additional security
- Set up Virtual Network for network isolation
- Use Managed Identities for secure access to Azure resources
- Enable encryption for PostgreSQL and Storage Account
- Configure Azure Security Center for security monitoring
