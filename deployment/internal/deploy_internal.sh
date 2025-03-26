#!/bin/bash
# Internal Government Server Deployment Script for WAAP
# This script automates the deployment of the WAAP application on internal government servers

# Exit on error
set -e

# Configuration - Replace these values with your own
APP_USER="waap"
APP_GROUP="waap"
APP_DIR="/home/waap/waap_project"
LOG_DIR="/var/log/waap"
DB_NAME="waap_db"
DB_USER="waap_user"
DB_PASSWORD="secure_password"
DOMAIN="your.domain.gov.ca"

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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "This script must be run as root"
    exit 1
fi

# Check if the application user exists
if ! id -u $APP_USER >/dev/null 2>&1; then
    echo_status "Creating application user $APP_USER"
    useradd -m -s /bin/bash $APP_USER
    passwd $APP_USER
else
    echo_status "Application user $APP_USER already exists"
fi

# Install system dependencies
echo_status "Installing system dependencies"
if [ -f /etc/redhat-release ]; then
    # RHEL/CentOS
    yum update -y
    yum install -y python3.12 python3.12-devel python3.12-pip postgresql-devel nginx git
elif [ -f /etc/debian_version ]; then
    # Ubuntu/Debian
    apt update
    apt upgrade -y
    apt install -y python3.12 python3.12-dev python3.12-pip libpq-dev nginx git
else
    echo_error "Unsupported operating system"
    exit 1
fi

# Set up PostgreSQL if not already installed
if ! command -v psql &> /dev/null; then
    echo_status "Installing PostgreSQL"
    if [ -f /etc/redhat-release ]; then
        # RHEL/CentOS
        yum install -y postgresql-server postgresql-contrib
        postgresql-setup initdb
        systemctl enable postgresql
        systemctl start postgresql
    elif [ -f /etc/debian_version ]; then
        # Ubuntu/Debian
        apt install -y postgresql postgresql-contrib
    fi
else
    echo_status "PostgreSQL is already installed"
fi

# Create database and user if they don't exist
echo_status "Setting up database"
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
    sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
    sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
else
    echo_status "Database $DB_NAME already exists"
fi

# Create log directory
echo_status "Creating log directory"
mkdir -p $LOG_DIR
chown $APP_USER:$APP_GROUP $LOG_DIR

# Clone or update the repository
if [ ! -d "$APP_DIR" ]; then
    echo_status "Cloning repository"
    mkdir -p $(dirname $APP_DIR)
    git clone https://your-git-repository-url/waap_project.git $APP_DIR
    chown -R $APP_USER:$APP_GROUP $APP_DIR
else
    echo_status "Repository already exists, updating"
    cd $APP_DIR
    sudo -u $APP_USER git pull
fi

# Set up virtual environment
echo_status "Setting up virtual environment"
cd $APP_DIR
if [ ! -d "venv" ]; then
    sudo -u $APP_USER python3.12 -m venv venv
fi
sudo -u $APP_USER bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn"

# Create .env file
echo_status "Creating environment file"
cat > $APP_DIR/.env << EOF
DJANGO_SETTINGS_MODULE=waap_project.settings_production
DJANGO_SECRET_KEY=$(openssl rand -base64 32)
ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432
RECAPTCHA_PUBLIC_KEY=your_recaptcha_public_key
RECAPTCHA_PRIVATE_KEY=your_recaptcha_private_key
EMAIL_HOST=your_email_host
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email_user
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=noreply@$DOMAIN
LOG_FILE=$LOG_DIR/waap.log
EOF
chown $APP_USER:$APP_GROUP $APP_DIR/.env
chmod 640 $APP_DIR/.env

# Apply migrations and collect static files
echo_status "Initializing application"
cd $APP_DIR
sudo -u $APP_USER bash -c "source venv/bin/activate && python manage.py migrate --settings=waap_project.settings_production && python manage.py collectstatic --noinput --settings=waap_project.settings_production"

# Set up Gunicorn service
echo_status "Setting up Gunicorn service"
cat > /etc/systemd/system/waap.service << EOF
[Unit]
Description=WAAP Gunicorn daemon
After=network.target

[Service]
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:$APP_DIR/waap.sock waap_project.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable waap
systemctl start waap || systemctl restart waap

# Set up Nginx
echo_status "Setting up Nginx"
if [ -d /etc/nginx/sites-available ]; then
    # Debian/Ubuntu style
    cat > /etc/nginx/sites-available/waap << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root $APP_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/waap.sock;
    }
}
EOF
    if [ ! -f /etc/nginx/sites-enabled/waap ]; then
        ln -s /etc/nginx/sites-available/waap /etc/nginx/sites-enabled/
    fi
else
    # RHEL/CentOS style
    cat > /etc/nginx/conf.d/waap.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root $APP_DIR;
    }

    location / {
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://unix:$APP_DIR/waap.sock;
    }
}
EOF
fi

# Test Nginx configuration
nginx -t
systemctl restart nginx

# Set up auto-expiration cron job
echo_status "Setting up auto-expiration cron job"
crontab -u $APP_USER -l 2>/dev/null | grep -v "expire_job_postings" | { cat; echo "0 0 * * * cd $APP_DIR && source venv/bin/activate && python manage.py expire_job_postings --settings=waap_project.settings_production >> $LOG_DIR/expire_job_postings.log 2>&1"; } | crontab -u $APP_USER -

# Set up log rotation
echo_status "Setting up log rotation"
cat > /etc/logrotate.d/waap << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $APP_USER $APP_GROUP
}
EOF

# Set up database backup script
echo_status "Setting up database backup script"
BACKUP_DIR="/home/$APP_USER/backups"
mkdir -p $BACKUP_DIR
chown $APP_USER:$APP_GROUP $BACKUP_DIR

cat > /home/$APP_USER/backup_db.sh << EOF
#!/bin/bash
BACKUP_DIR="$BACKUP_DIR"
TIMESTAMP=\$(date +"%Y%m%d_%H%M%S")
mkdir -p \$BACKUP_DIR
pg_dump $DB_NAME -U $DB_USER -h localhost > \$BACKUP_DIR/waap_db_\$TIMESTAMP.sql
find \$BACKUP_DIR -name "waap_db_*.sql" -type f -mtime +7 -delete
EOF

chmod +x /home/$APP_USER/backup_db.sh
chown $APP_USER:$APP_GROUP /home/$APP_USER/backup_db.sh

crontab -u $APP_USER -l 2>/dev/null | grep -v "backup_db.sh" | { cat; echo "0 2 * * * /home/$APP_USER/backup_db.sh"; } | crontab -u $APP_USER -

# Configure firewall
echo_status "Configuring firewall"
if command -v ufw &> /dev/null; then
    # Ubuntu/Debian with UFW
    ufw allow 'Nginx Full'
    ufw --force enable
elif command -v firewall-cmd &> /dev/null; then
    # RHEL/CentOS with firewalld
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
fi

echo_status "Deployment complete!"
echo_status "Next steps:"
echo_status "1. Set up SSL/TLS for secure HTTPS connections"
echo_status "2. Configure your domain DNS to point to this server"
echo_status "3. Test the application at http://$DOMAIN"
echo_status "4. Set up monitoring and alerting"
