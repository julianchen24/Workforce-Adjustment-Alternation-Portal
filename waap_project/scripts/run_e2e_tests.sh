#!/bin/bash
# End-to-End Testing Script for WAAP
# This script runs comprehensive end-to-end tests in a staging environment

# Exit on error
set -e

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

# Configuration - Replace these values with your staging environment details
STAGING_DIR="/path/to/staging/waap_project"
VENV_PATH="$STAGING_DIR/venv"
SETTINGS_MODULE="waap_project.settings_production"
LOG_FILE="$STAGING_DIR/e2e_test_results.log"

# Check if the staging directory exists
if [ ! -d "$STAGING_DIR" ]; then
    echo_error "Staging directory not found: $STAGING_DIR"
    exit 1
fi

# Navigate to the staging directory
cd "$STAGING_DIR"

# Activate the virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo_error "Virtual environment not found: $VENV_PATH"
    exit 1
fi

echo_status "Activating virtual environment"
source "$VENV_PATH/bin/activate"

# Check if Django is installed
if ! python -c "import django" &> /dev/null; then
    echo_error "Django is not installed in the virtual environment"
    exit 1
fi

# Start the test log
echo "=== WAAP End-to-End Test Results - $(date) ===" > "$LOG_FILE"

# Run the tests
echo_status "Running end-to-end tests"

# Test 1: Authentication System
echo_status "Testing authentication system"
echo -e "\n=== Authentication System Tests ===" >> "$LOG_FILE"
python manage.py test waap.tests_integration.IntegrationTest.test_end_to_end_workflow --settings="$SETTINGS_MODULE" -v 2 >> "$LOG_FILE" 2>&1 || {
    echo_error "Authentication system tests failed"
    echo "Authentication system tests failed" >> "$LOG_FILE"
}

# Test 2: Admin Moderation Workflow
echo_status "Testing admin moderation workflow"
echo -e "\n=== Admin Moderation Workflow Tests ===" >> "$LOG_FILE"
python manage.py test waap.tests_integration.IntegrationTest.test_admin_moderation_workflow --settings="$SETTINGS_MODULE" -v 2 >> "$LOG_FILE" 2>&1 || {
    echo_error "Admin moderation workflow tests failed"
    echo "Admin moderation workflow tests failed" >> "$LOG_FILE"
}

# Test 3: Auto-Expiration Workflow
echo_status "Testing auto-expiration workflow"
echo -e "\n=== Auto-Expiration Workflow Tests ===" >> "$LOG_FILE"
python manage.py test waap.tests_integration.IntegrationTest.test_auto_expiration_workflow --settings="$SETTINGS_MODULE" -v 2 >> "$LOG_FILE" 2>&1 || {
    echo_error "Auto-expiration workflow tests failed"
    echo "Auto-expiration workflow tests failed" >> "$LOG_FILE"
}

# Test 4: Integrated Workflow with Moderation and Expiration
echo_status "Testing integrated workflow with moderation and expiration"
echo -e "\n=== Integrated Workflow Tests ===" >> "$LOG_FILE"
python manage.py test waap.tests_integration.IntegrationTest.test_integrated_workflow_with_moderation_and_expiration --settings="$SETTINGS_MODULE" -v 2 >> "$LOG_FILE" 2>&1 || {
    echo_error "Integrated workflow tests failed"
    echo "Integrated workflow tests failed" >> "$LOG_FILE"
}

# Test 5: Run the expire_job_postings command
echo_status "Testing expire_job_postings command"
echo -e "\n=== Expire Job Postings Command Test ===" >> "$LOG_FILE"
python manage.py expire_job_postings --settings="$SETTINGS_MODULE" --dry-run >> "$LOG_FILE" 2>&1 || {
    echo_error "expire_job_postings command test failed"
    echo "expire_job_postings command test failed" >> "$LOG_FILE"
}

# Test 6: Check database connections
echo_status "Testing database connections"
echo -e "\n=== Database Connection Test ===" >> "$LOG_FILE"
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$SETTINGS_MODULE')
import django
django.setup()
from django.db import connections
connections['default'].ensure_connection()
print('Database connection successful')
" >> "$LOG_FILE" 2>&1 || {
    echo_error "Database connection test failed"
    echo "Database connection test failed" >> "$LOG_FILE"
}

# Test 7: Check email configuration
echo_status "Testing email configuration"
echo -e "\n=== Email Configuration Test ===" >> "$LOG_FILE"
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$SETTINGS_MODULE')
import django
django.setup()
from django.core.mail import send_mail
try:
    send_mail(
        'Test Email from WAAP',
        'This is a test email from the WAAP application.',
        'noreply@example.com',
        ['test@example.com'],
        fail_silently=False,
    )
    print('Email test successful')
except Exception as e:
    print(f'Email test failed: {e}')
    exit(1)
" >> "$LOG_FILE" 2>&1 || {
    echo_error "Email configuration test failed"
    echo "Email configuration test failed" >> "$LOG_FILE"
}

# Test 8: Check static files
echo_status "Testing static files"
echo -e "\n=== Static Files Test ===" >> "$LOG_FILE"
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '$SETTINGS_MODULE')
import django
django.setup()
from django.contrib.staticfiles.storage import staticfiles_storage
try:
    url = staticfiles_storage.url('style.css')
    print(f'Static file URL: {url}')
    print('Static files test successful')
except Exception as e:
    print(f'Static files test failed: {e}')
    exit(1)
" >> "$LOG_FILE" 2>&1 || {
    echo_error "Static files test failed"
    echo "Static files test failed" >> "$LOG_FILE"
}

# Deactivate the virtual environment
deactivate

# Check if any tests failed
if grep -q "failed" "$LOG_FILE"; then
    echo_error "Some tests failed. Check $LOG_FILE for details."
    exit 1
else
    echo_status "All tests passed successfully!"
    echo -e "\n=== All tests passed successfully! ===" >> "$LOG_FILE"
fi

echo_status "Test results saved to $LOG_FILE"
