from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.db import connections
from django.utils import timezone
import unittest
from datetime import timedelta
from .models import Department, JobPosting

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
        
        # During tests, Django automatically changes the email backend to 'locmem'
        self.assertEqual(settings.EMAIL_BACKEND, 'django.core.mail.backends.locmem.EmailBackend')
        
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


class JobPostingModelTest(TestCase):
    """Test the JobPosting model."""
    
    def setUp(self):
        """Set up test data."""
        # Create a department
        self.department = Department.objects.create(name="Information Technology")
        
        # Create a job posting with explicit expiration date
        self.job_posting_explicit = JobPosting.objects.create(
            job_title="Software Developer",
            department=self.department,
            location="Ottawa, ON",
            classification="PERMANENT",
            alternation_criteria={"experience": "3+ years", "skills": ["Python", "Django"]},
            language_profile="BILINGUAL",
            contact_email="hr@example.com",
            expiration_date=timezone.now() + timedelta(days=15)
        )
        
        # Create a job posting without explicit expiration date (should default to 30 days)
        tomorrow = timezone.now() + timedelta(days=1)
        self.job_posting_default = JobPosting(
            job_title="Data Analyst",
            department=self.department,
            location="Toronto, ON",
            classification="CONTRACT",
            language_profile="ENGLISH",
            contact_email="recruiting@example.com"
        )
        # Save without expiration_date to test the default behavior
        self.job_posting_default.save()
    
    def test_job_posting_creation(self):
        """Test that job postings can be created with valid data."""
        self.assertEqual(JobPosting.objects.count(), 2)
        self.assertEqual(self.job_posting_explicit.job_title, "Software Developer")
        self.assertEqual(self.job_posting_explicit.department.name, "Information Technology")
        self.assertEqual(self.job_posting_explicit.location, "Ottawa, ON")
        self.assertEqual(self.job_posting_explicit.classification, "PERMANENT")
        self.assertEqual(self.job_posting_explicit.language_profile, "BILINGUAL")
        self.assertEqual(self.job_posting_explicit.contact_email, "hr@example.com")
        
        # Test JSON field
        self.assertEqual(self.job_posting_explicit.alternation_criteria["experience"], "3+ years")
        self.assertIn("Python", self.job_posting_explicit.alternation_criteria["skills"])
    
    def test_auto_populated_fields(self):
        """Test that auto-populated fields behave correctly."""
        # Test posting_date is auto-populated
        self.assertIsNotNone(self.job_posting_explicit.posting_date)
        self.assertIsNotNone(self.job_posting_default.posting_date)
        
        # Test created_at and updated_at are auto-populated
        self.assertIsNotNone(self.job_posting_explicit.created_at)
        self.assertIsNotNone(self.job_posting_explicit.updated_at)
        
        # Test default expiration_date (30 days from posting_date)
        # Allow for a small time difference due to test execution
        expected_expiration = self.job_posting_default.posting_date + timedelta(days=30)
        difference = abs((expected_expiration - self.job_posting_default.expiration_date).total_seconds())
        self.assertLess(difference, 10)  # Less than 10 seconds difference
    
    def test_is_active_property(self):
        """Test the is_active property."""
        # Current job postings should be active
        self.assertTrue(self.job_posting_explicit.is_active)
        self.assertTrue(self.job_posting_default.is_active)
        
        # Create an expired job posting
        expired_job = JobPosting.objects.create(
            job_title="Expired Position",
            department=self.department,
            location="Montreal, QC",
            classification="TEMPORARY",
            language_profile="FRENCH",
            expiration_date=timezone.now() - timedelta(days=1)  # 1 day in the past
        )
        
        # Expired job should not be active
        self.assertFalse(expired_job.is_active)
