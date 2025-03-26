# WAAP Deployment and Operations Guide

This comprehensive guide outlines the deployment process, testing procedures, and operational tasks for the WAAP (Web Application for Agency Postings) application.

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Pre-Deployment Preparation](#pre-deployment-preparation)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Testing Procedures](#testing-procedures)
6. [Scheduled Tasks](#scheduled-tasks)
7. [Monitoring and Maintenance](#monitoring-and-maintenance)
8. [Backup and Recovery](#backup-and-recovery)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting](#troubleshooting)

## Deployment Options

The WAAP application can be deployed to various environments:

1. **Microsoft Azure**: Cloud-based deployment using Azure App Service, Azure Database for PostgreSQL, and Azure Storage.
2. **Internal Government Servers**: On-premises deployment on government-owned infrastructure.

Detailed deployment guides for each option are available in the `deployment` directory:

- [Azure Deployment Guide](../deployment/azure/README.md)
- [Internal Server Deployment Guide](../deployment/internal/README.md)

## Pre-Deployment Preparation

Before deploying the application, ensure the following prerequisites are met:

### 1. Environment Requirements

- Python 3.12+
- PostgreSQL 12+
- Web server (Nginx or Apache)
- Application server (Gunicorn)

### 2. Security Requirements

- SSL/TLS certificates
- Secure database credentials
- reCAPTCHA keys (for production)
- Email service credentials

### 3. Configuration Files

- Production settings file (`settings_production.py`)
- Environment variables or `.env` file
- Web server configuration

## Deployment Steps

The deployment process varies depending on the target environment. Automated deployment scripts are provided for each environment:

### Azure Deployment

```bash
# Navigate to the deployment directory
cd deployment/azure

# Update configuration in deploy_azure.sh
nano deploy_azure.sh

# Make the script executable
chmod +x deploy_azure.sh

# Run the deployment script
./deploy_azure.sh
```

### Internal Server Deployment

```bash
# Navigate to the deployment directory
cd deployment/internal

# Update configuration in deploy_internal.sh
nano deploy_internal.sh

# Make the script executable
chmod +x deploy_internal.sh

# Run the deployment script (as root)
sudo ./deploy_internal.sh
```

## Post-Deployment Configuration

After deploying the application, perform the following configuration steps:

### 1. Database Migrations

```bash
# For Azure
az webapp ssh --resource-group waap-resource-group --name waap-app
cd site/wwwroot
python manage.py migrate --settings=waap_project.settings_production

# For internal servers
cd /home/waap/waap_project
source venv/bin/activate
python manage.py migrate --settings=waap_project.settings_production
```

### 2. Static Files Collection

```bash
# For Azure
python manage.py collectstatic --settings=waap_project.settings_production

# For internal servers
python manage.py collectstatic --settings=waap_project.settings_production
```

### 3. Create Superuser

```bash
# For both environments
python manage.py createsuperuser --settings=waap_project.settings_production
```

### 4. Configure SSL/TLS

For Azure, SSL is configured automatically through the Azure portal.

For internal servers:

```bash
# Using Let's Encrypt
sudo certbot --nginx -d your.domain.gov.ca

# Or using internal CA certificates
sudo cp your_cert.pem /etc/ssl/waap/cert.pem
sudo cp your_key.pem /etc/ssl/waap/key.pem
sudo nginx -t
sudo systemctl restart nginx
```

## Testing Procedures

Comprehensive testing should be performed before and after deployment. Detailed testing procedures are available in the [Testing Procedures](testing_procedures.md) document.

### Key Testing Areas

1. **Authentication System**:
   - One-time token generation and verification
   - Session management
   - User permissions

2. **Job Posting Management**:
   - Creation, viewing, and deletion of job postings
   - Filtering and searching
   - Expiration and anonymization

3. **Contact System**:
   - Contact form submission
   - Email delivery
   - CAPTCHA validation

4. **Moderation System**:
   - Admin moderation actions
   - Status changes and visibility

5. **Integration Testing**:
   - End-to-end workflow testing
   - Component interaction testing

### Running Tests

```bash
# Run all tests
python manage.py test waap

# Run integration tests
python manage.py test waap.tests_integration

# Run specific test
python manage.py test waap.tests_integration.IntegrationTest.test_end_to_end_workflow
```

## Scheduled Tasks

The WAAP application includes scheduled tasks that need to be configured to run automatically.

### Auto-Expiration Task

The `expire_job_postings` management command automatically expires and anonymizes job postings older than their expiration date.

#### Configuration Options

1. **Azure WebJobs**:
   - Already configured by the deployment script
   - Runs daily at midnight

2. **Cron (Linux/Unix/macOS)**:
   ```bash
   # Edit the crontab for the application user
   sudo -u waap crontab -e
   
   # Add the following line to run daily at midnight
   0 0 * * * cd /home/waap/waap_project && source venv/bin/activate && python manage.py expire_job_postings --settings=waap_project.settings_production >> /var/log/waap/expire_job_postings.log 2>&1
   ```

3. **Windows Task Scheduler**:
   - Create a new task to run daily at midnight
   - Program: `C:\path\to\python.exe`
   - Arguments: `C:\path\to\waap_project\manage.py expire_job_postings --settings=waap_project.settings_production`
   - Start in: `C:\path\to\waap_project`

4. **Django-crontab**:
   ```bash
   # Install django-crontab
   pip install django-crontab
   
   # Add to INSTALLED_APPS in settings_production.py
   INSTALLED_APPS = [
       # ...
       'django_crontab',
       # ...
   ]
   
   # Add the CRONJOBS setting
   CRONJOBS = [
       ('0 0 * * *', 'django.core.management.call_command', ['expire_job_postings']),
   ]
   
   # Apply the crontab
   python manage.py crontab add
   ```

### Monitoring the Scheduled Tasks

Monitor the execution of scheduled tasks through logs:

```bash
# View the log file
tail -f /var/log/waap/expire_job_postings.log

# Check the cron job status
sudo grep CRON /var/log/syslog
```

## Monitoring and Maintenance

### Application Monitoring

1. **Azure Application Insights**:
   - Already configured by the deployment script
   - Access through the Azure portal

2. **Log Files**:
   - Application logs: `/var/log/waap/waap.log`
   - Scheduled task logs: `/var/log/waap/expire_job_postings.log`
   - Web server logs: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`

3. **Database Monitoring**:
   - PostgreSQL logs: `/var/log/postgresql/postgresql-12-main.log`
   - Connection pooling: Configured with `CONN_MAX_AGE=600` in settings

### Regular Maintenance Tasks

1. **Database Maintenance**:
   ```bash
   # Connect to the database
   sudo -u postgres psql
   
   # Analyze and vacuum the database
   ANALYZE;
   VACUUM FULL;
   ```

2. **Log Rotation**:
   - Configured automatically by the deployment scripts
   - Check configuration in `/etc/logrotate.d/waap`

3. **Backup Verification**:
   ```bash
   # List backups
   ls -la /home/waap/backups
   
   # Test restore (to a temporary database)
   createdb waap_test_restore
   psql waap_test_restore < /home/waap/backups/waap_db_YYYYMMDD_HHMMSS.sql
   ```

## Backup and Recovery

### Backup Strategy

1. **Database Backups**:
   - Daily automated backups configured by the deployment scripts
   - Retention period: 7 days
   - Location: `/home/waap/backups` (internal servers) or Azure Backup (Azure)

2. **Application Code**:
   - Stored in version control (Git)
   - Deploy from version control for recovery

3. **Configuration Files**:
   - Back up `.env` file and web server configurations
   - Store securely with restricted access

### Recovery Procedures

1. **Database Recovery**:
   ```bash
   # Restore from backup
   createdb waap_db
   psql waap_db < /home/waap/backups/waap_db_YYYYMMDD_HHMMSS.sql
   ```

2. **Application Recovery**:
   ```bash
   # Clone the repository
   git clone https://your-git-repository-url/waap_project.git
   
   # Set up the environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Restore configuration
   cp /path/to/backup/.env .env
   
   # Apply migrations
   python manage.py migrate --settings=waap_project.settings_production
   ```

## Security Considerations

### Authentication Security

- One-time tokens are secure and time-limited
- Sessions are secured with `SESSION_COOKIE_SECURE=True`
- HTTPS is enforced with `SECURE_SSL_REDIRECT=True`

### Data Protection

- Sensitive data is anonymized after expiration
- Database credentials are stored securely
- CSRF protection is enabled

### Server Hardening

- Firewall is configured to allow only necessary traffic
- Web server is configured with secure headers
- File permissions are restricted

## Troubleshooting

### Common Issues and Solutions

1. **Application Not Starting**:
   - Check the application logs: `/var/log/waap/waap.log`
   - Check the systemd logs: `sudo journalctl -u waap`
   - Verify the virtual environment is activated

2. **Database Connection Issues**:
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify database credentials in `.env`
   - Check database logs: `/var/log/postgresql/postgresql-12-main.log`

3. **Static Files Not Loading**:
   - Check Nginx configuration
   - Verify `STATIC_ROOT` and `STATICFILES_DIRS` settings
   - Run `collectstatic` again

4. **Email Not Sending**:
   - Verify email settings in `.env`
   - Check email service is accessible
   - Test with Django's `send_mail` command

5. **Scheduled Tasks Not Running**:
   - Check cron configuration: `sudo -u waap crontab -l`
   - Verify log file permissions
   - Run the command manually to check for errors

### Getting Help

For additional assistance:

1. Check the Django documentation: https://docs.djangoproject.com/
2. Review the deployment guides in the `deployment` directory
3. Contact the development team at support@waap.gov.ca
