"""
Database setup script for WAAP project.
This script helps create the PostgreSQL database and apply migrations.
"""

import os
import sys
import subprocess
import getpass

def run_command(command):
    """Run a shell command and print the output."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode == 0

def setup_database():
    """Set up the PostgreSQL database for the WAAP project."""
    print("=" * 50)
    print("WAAP Project Database Setup")
    print("=" * 50)
    
    # Check if PostgreSQL is installed
    if not run_command("psql --version"):
        print("PostgreSQL is not installed or not in PATH. Please install PostgreSQL first.")
        return False
    
    # Get database credentials
    db_name = input("Database name (default: waap_db): ") or "waap_db"
    db_user = input("Database user (default: postgres): ") or "postgres"
    db_password = getpass.getpass("Database password (default: postgres): ") or "postgres"
    db_host = input("Database host (default: localhost): ") or "localhost"
    db_port = input("Database port (default: 5432): ") or "5432"
    
    # Create database
    print("\nCreating database...")
    create_db_command = f'psql -U {db_user} -h {db_host} -p {db_port} -c "CREATE DATABASE {db_name};"'
    if not run_command(create_db_command):
        print("Failed to create database. Make sure PostgreSQL is running and credentials are correct.")
        return False
    
    # Update settings.py with the provided credentials
    print("\nUpdating settings.py...")
    settings_path = os.path.join("waap_project", "settings.py")
    
    try:
        with open(settings_path, 'r') as f:
            settings_content = f.read()
        
        # Replace database settings
        import re
        db_pattern = r'DATABASES = \{.*?\'default\': \{.*?\}.*?\}'
        db_replacement = f'''DATABASES = {{
    "default": {{
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "{db_name}",
        "USER": "{db_user}",
        "PASSWORD": "{db_password}",
        "HOST": "{db_host}",
        "PORT": "{db_port}",
    }}
}}'''
        
        updated_settings = re.sub(db_pattern, db_replacement, settings_content, flags=re.DOTALL)
        
        with open(settings_path, 'w') as f:
            f.write(updated_settings)
            
        print("Settings updated successfully.")
    except Exception as e:
        print(f"Failed to update settings: {e}")
        return False
    
    # Apply migrations
    print("\nApplying migrations...")
    if not run_command("python manage.py makemigrations"):
        print("Failed to make migrations.")
        return False
    
    if not run_command("python manage.py migrate"):
        print("Failed to apply migrations.")
        return False
    
    # Create superuser
    print("\nCreating superuser...")
    if not run_command("python manage.py createsuperuser"):
        print("Failed to create superuser.")
        return False
    
    print("\n" + "=" * 50)
    print("Database setup completed successfully!")
    print("=" * 50)
    print("\nYou can now run the development server with:")
    print("python manage.py runserver")
    
    return True

if __name__ == "__main__":
    # Make sure we're in the right directory
    if not os.path.exists("manage.py"):
        print("This script must be run from the project root directory (where manage.py is located).")
        sys.exit(1)
    
    setup_database()
