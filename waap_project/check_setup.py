"""
Setup verification script for WAAP project.
This script checks if the project is properly set up and ready to run.
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path

def run_command(command):
    """Run a shell command and return the output and success status."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode == 0

def check_python_version():
    """Check if Python version is compatible."""
    import platform
    python_version = platform.python_version()
    print(f"Python version: {python_version}")
    major, minor, _ = map(int, python_version.split('.'))
    if major < 3 or (major == 3 and minor < 8):
        print("❌ Python version 3.8 or higher is required.")
        return False
    print("✅ Python version is compatible.")
    return True

def check_django_installation():
    """Check if Django is installed."""
    try:
        import django
        print(f"Django version: {django.get_version()}")
        print("✅ Django is installed.")
        return True
    except ImportError:
        print("❌ Django is not installed. Run 'pip install -r requirements.txt'.")
        return False

def check_postgresql():
    """Check if PostgreSQL is installed and accessible."""
    stdout, stderr, success = run_command("psql --version")
    if not success:
        print("❌ PostgreSQL is not installed or not in PATH.")
        return False
    print(f"✅ PostgreSQL is installed: {stdout.strip()}")
    return True

def check_database_connection():
    """Check if the database connection is working."""
    # Try to import Django settings
    try:
        sys.path.insert(0, os.getcwd())
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waap_project.settings')
        import django
        django.setup()
        
        from django.db import connections
        from django.db.utils import OperationalError
        
        conn = connections['default']
        try:
            conn.cursor()
            print("✅ Database connection is working.")
            return True
        except OperationalError:
            print("❌ Database connection failed. Make sure PostgreSQL is running and the database exists.")
            return False
    except Exception as e:
        print(f"❌ Error checking database connection: {e}")
        return False

def check_migrations():
    """Check if migrations have been applied."""
    stdout, stderr, success = run_command("python manage.py showmigrations")
    if not success:
        print("❌ Failed to check migrations.")
        return False
    
    if "[X]" in stdout:
        print("✅ Some migrations have been applied.")
        return True
    else:
        print("❌ No migrations have been applied. Run 'python manage.py migrate'.")
        return False

def check_static_files():
    """Check if static files directory exists."""
    static_dir = Path("static")
    if static_dir.exists() and static_dir.is_dir():
        print("✅ Static files directory exists.")
        return True
    else:
        print("❌ Static files directory does not exist. Create it with 'mkdir static'.")
        return False

def main():
    """Run all checks and report results."""
    print("=" * 50)
    print("WAAP Project Setup Verification")
    print("=" * 50)
    
    # Make sure we're in the right directory
    if not os.path.exists("manage.py"):
        print("This script must be run from the project root directory (where manage.py is located).")
        sys.exit(1)
    
    checks = [
        ("Python version", check_python_version),
        ("Django installation", check_django_installation),
        ("PostgreSQL installation", check_postgresql),
        ("Database connection", check_database_connection),
        ("Migrations", check_migrations),
        ("Static files", check_static_files),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        result = check_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All checks passed! The project is ready to run.")
        print("You can start the development server with:")
        print("python manage.py runserver")
    else:
        print("❌ Some checks failed. Please fix the issues before running the project.")
    print("=" * 50)
    
    return all_passed

if __name__ == "__main__":
    main()
