from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.db import connections
import unittest

class ProjectSetupTest(TestCase):
    """Test basic project setup and configuration."""
    
    def test_project_loads(self):
        """Test that the Django project loads successfully."""
        try:
            client = Client()
            response = client.get('/admin/login/')  # Using admin login page as it's available by default
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.fail(f"Project failed to load: {e}")
        
    def test_settings_configuration(self):
        """Test that key settings are properly configured."""
        # Test database configuration
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')
        
        # Test installed apps
        self.assertIn('waap', settings.INSTALLED_APPS)
        
        # Test email backend
        self.assertEqual(settings.EMAIL_BACKEND, 'django.core.mail.backends.console.EmailBackend')
        
        # Test static files configuration
        self.assertTrue(hasattr(settings, 'STATIC_ROOT'))
        self.assertTrue(hasattr(settings, 'STATICFILES_DIRS'))

    @unittest.skipIf(not connections['default'].is_usable(), "Database connection not available")
    def test_database_connection(self):
        """Test that the database connection is working."""
        # This test will be skipped if the database connection is not available
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
