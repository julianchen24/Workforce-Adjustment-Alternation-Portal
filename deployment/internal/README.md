# Internal Government Server Deployment Guide for WAAP

This guide provides instructions for deploying the WAAP application on internal government servers, which may have specific security and compliance requirements.

## Prerequisites

- Linux server (RHEL, CentOS, or Ubuntu preferred)
- Python 3.12+
- PostgreSQL 12+
- Nginx or Apache web server
- Supervisor or systemd for process management
- Git

## Deployment Steps

### 1. Server Preparation

#### System Updates and Dependencies

```bash
# For RHEL/CentOS
sudo yum update -y
sudo yum install -y python3.12 python3.12-devel python3.12-pip postgresql-devel nginx git

# For Ubuntu
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-dev python3.12-pip libpq-dev nginx git
```

#### Create Application User

```bash
sudo useradd -m -s /bin/bash waap
sudo passwd waap
```

### 2. Database Setup

#### Install PostgreSQL (if not already installed)

```bash
# For RHEL/CentOS
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql

# For Ubuntu
sudo apt install -y postgresql postgresql-contrib
```

#### Create Database and User

```bash
sudo -u postgres psql
```

```sql
CREATE USER waap_user WITH PASSWORD 'secure_password';
CREATE DATABASE waap_db OWNER waap_user;
ALTER ROLE waap_user SET client_encoding TO 'utf8';
ALTER ROLE waap_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE waap_user SET timezone TO 'UTC';
\q
```

### 3. Application Setup

#### Clone the Repository

```bash
sudo -u waap bash
cd /home/waap
git clone https://your-git-repository-url/waap_project.git
cd waap_project
```

#### Set Up Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

#### Create Production Settings

Create a `.env` file in the project root:

```bash
cat > .env << EOF
DJANGO_SETTINGS_MODULE=waap_project.settings_production
DJANGO_SECRET_KEY=your_secure_secret_key
ALLOWED_HOSTS=your.domain.gov.ca,localhost,127.0.0.1
DB_NAME=waap_db
DB_USER=waap_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432
RECAPTCHA_PUBLIC_KEY=your_recaptcha_public_key
RECAPTCHA_PRIVATE_KEY=your_recaptcha_private_key
EMAIL_HOST=your_email_host
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email_user
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=noreply@your.domain.gov.ca
LOG_FILE=/var/log/waap/waap.log
EOF
```

#### Initialize the Application

```bash
# Create log directory
sudo mkdir -p /var/log/waap
sudo chown waap:waap /var/log/waap

# Apply migrations and collect static files
python manage.py migrate --settings=waap_project.settings_production
python manage.py collectstatic --settings=waap_project.settings_production
```

### 4. Web Server Configuration

#### Set Up Gunicorn

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/waap.service
```

Add the following content:

```ini
[Unit]
Description=WAAP Gunicorn daemon
After=network.target

[Service]
User=waap
Group=waap
WorkingDirectory=/home/waap/waap_project
EnvironmentFile=/home/waap/waap_project/.env
ExecStart=/home/waap/waap_project/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/home/waap/waap_project/waap.sock waap_project.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable waap
sudo systemctl start waap
```

#### Configure Nginx

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/waap
```

Add the following content:

```nginx
server {
    listen 80;
    server_name your.domain.gov.ca;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/waap/waap_project;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/waap/waap_project/waap.sock;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/waap /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 5. SSL Configuration

For government servers, SSL is typically mandatory. Set up SSL with Let's Encrypt or your government's internal CA:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.gov.ca
```

Or for internal CA:

```bash
# Place your certificate and key files
sudo mkdir -p /etc/ssl/waap
sudo cp your_cert.pem /etc/ssl/waap/cert.pem
sudo cp your_key.pem /etc/ssl/waap/key.pem

# Update Nginx configuration
sudo nano /etc/nginx/sites-available/waap
```

Update the Nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name your.domain.gov.ca;

    ssl_certificate /etc/ssl/waap/cert.pem;
    ssl_certificate_key /etc/ssl/waap/key.pem;
    
    # Strong SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # HSTS (optional, but recommended)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/waap/waap_project;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/waap/waap_project/waap.sock;
    }
}

server {
    listen 80;
    server_name your.domain.gov.ca;
    return 301 https://$host$request_uri;
}
```

Restart Nginx:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Set Up Auto-Expiration Task

Create a cron job to run the expire_job_postings command:

```bash
sudo -u waap crontab -e
```

Add the following line:

```
0 0 * * * cd /home/waap/waap_project && source venv/bin/activate && python manage.py expire_job_postings --settings=waap_project.settings_production >> /var/log/waap/expire_job_postings.log 2>&1
```

### 7. Security Hardening

#### Firewall Configuration

```bash
# For Ubuntu with UFW
sudo ufw allow 'Nginx Full'
sudo ufw enable

# For RHEL/CentOS with firewalld
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

#### SELinux Configuration (for RHEL/CentOS)

```bash
sudo setsebool -P httpd_can_network_connect 1
sudo semanage fcontext -a -t httpd_sys_content_t "/home/waap/waap_project/static(/.*)?"
sudo restorecon -Rv /home/waap/waap_project/static
```

#### Secure File Permissions

```bash
# Ensure sensitive files are not world-readable
chmod 640 /home/waap/waap_project/.env
chmod 750 /home/waap/waap_project
```

## Monitoring and Logging

### Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/waap
```

Add the following:

```
/var/log/waap/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 waap waap
}
```

### Set Up Monitoring (Optional)

For government environments, you may need to integrate with existing monitoring solutions like Nagios, Zabbix, or Prometheus.

## Backup Strategy

### Database Backup

Create a script for database backup:

```bash
sudo -u waap nano /home/waap/backup_db.sh
```

Add the following:

```bash
#!/bin/bash
BACKUP_DIR="/home/waap/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p $BACKUP_DIR
pg_dump waap_db -U waap_user -h localhost > $BACKUP_DIR/waap_db_$TIMESTAMP.sql
find $BACKUP_DIR -name "waap_db_*.sql" -type f -mtime +7 -delete
```

Make it executable and set up a cron job:

```bash
chmod +x /home/waap/backup_db.sh
sudo -u waap crontab -e
```

Add the following line:

```
0 2 * * * /home/waap/backup_db.sh
```

## Compliance Considerations

### Audit Logging

For government applications, audit logging may be required:

1. Enable Django's admin logging
2. Consider implementing a custom middleware for audit logging
3. Ensure logs are stored securely and for the required retention period

### Data Retention

Ensure your data retention policies comply with government regulations:

1. The auto-expiration functionality helps with this
2. Consider implementing additional data purging for other sensitive data

## Troubleshooting

- **Application not starting**: Check the systemd logs with `sudo journalctl -u waap`
- **Database connection issues**: Verify PostgreSQL is running and accessible
- **Static files not loading**: Check Nginx configuration and file permissions
- **Email not sending**: Verify email service configuration and network access

## Deployment Script

You can use the `deploy_internal.sh` script in this directory to automate parts of this deployment process.
