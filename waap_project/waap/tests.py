from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from django.db import connections
from django.utils import timezone
from django.core import mail
import unittest
from datetime import timedelta
from .models import Department, JobPosting, WaapUser, OneTimeToken

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


class OneTimeTokenModelTest(TestCase):
    """Test the OneTimeToken model."""
    
    def setUp(self):
        """Set up test data."""
        self.test_email = "test.user@government.ca"
        self.user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=self.test_email,
            department="Information Technology"
        )
    
    def test_token_creation(self):
        """Test that tokens can be created with valid data."""
        # Create a token using the class method
        token = OneTimeToken.create_for_email(self.test_email)
        
        # Check that the token was created correctly
        self.assertEqual(token.email, self.test_email)
        self.assertFalse(token.is_used)
        self.assertIsNotNone(token.token)
        self.assertIsNotNone(token.created_at)
        self.assertIsNotNone(token.expires_at)
        
        # Check that the token expires in 1 hour (with a small margin for test execution time)
        expected_expiration = token.created_at + timedelta(hours=1)
        difference = abs((expected_expiration - token.expires_at).total_seconds())
        self.assertLess(difference, 10)  # Less than 10 seconds difference
    
    def test_token_validity(self):
        """Test the is_valid property."""
        # Create a valid token
        valid_token = OneTimeToken.create_for_email(self.test_email)
        self.assertTrue(valid_token.is_valid)
        
        # Create an expired token
        expired_token = OneTimeToken.objects.create(
            email=self.test_email,
            token="expired-token",
            expires_at=timezone.now() - timedelta(minutes=5)  # 5 minutes in the past
        )
        self.assertFalse(expired_token.is_valid)
        
        # Create a used token
        used_token = OneTimeToken.objects.create(
            email=self.test_email,
            token="used-token",
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True
        )
        self.assertFalse(used_token.is_valid)


class OneTimeLoginViewsTest(TestCase):
    """Test the one-time login views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.test_email = "test.user@government.ca"
        self.user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=self.test_email,
            department="Information Technology"
        )
        
        # URL for requesting a login link
        self.login_request_url = reverse('waap:login_request')
    
    def test_login_request_get(self):
        """Test the login request page loads correctly."""
        response = self.client.get(self.login_request_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_request.html')
    
    def test_login_request_post_valid_email(self):
        """Test requesting a login link with a valid email."""
        response = self.client.post(self.login_request_url, {'email': self.test_email})
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_request_success.html')
        
        # Check that a token was created
        self.assertEqual(OneTimeToken.objects.filter(email=self.test_email).count(), 1)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.test_email])
        self.assertIn('Your WAAP Login Link', mail.outbox[0].subject)
    
    def test_login_request_post_invalid_email(self):
        """Test requesting a login link with an invalid email."""
        # Test with a non-government email
        response = self.client.post(self.login_request_url, {'email': 'invalid@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_request.html')
        self.assertContains(response, 'Please enter a valid government email address')
        
        # No token should be created
        self.assertEqual(OneTimeToken.objects.count(), 0)
        
        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)
    
    def test_login_verify_valid_token(self):
        """Test verifying a valid token."""
        # Create a token
        token = OneTimeToken.create_for_email(self.test_email)
        
        # Visit the verification URL
        verify_url = reverse('waap:login_verify', kwargs={'token': token.token})
        response = self.client.get(verify_url)
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_success.html')
        
        # Check that the token is marked as used
        token.refresh_from_db()
        self.assertTrue(token.is_used)
        
        # Check that the user is authenticated in the session
        self.assertEqual(self.client.session['waap_authenticated_user_id'], self.user.id)
    
    def test_login_verify_invalid_token(self):
        """Test verifying an invalid token."""
        # Visit the verification URL with a non-existent token
        verify_url = reverse('waap:login_verify', kwargs={'token': 'non-existent-token'})
        response = self.client.get(verify_url)
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_error.html')
        self.assertContains(response, 'Invalid login link')
        
        # Check that the user is not authenticated
        self.assertNotIn('waap_authenticated_user_id', self.client.session)
    
    def test_login_verify_expired_token(self):
        """Test verifying an expired token."""
        # Create an expired token
        expired_token = OneTimeToken.objects.create(
            email=self.test_email,
            token="expired-token",
            expires_at=timezone.now() - timedelta(minutes=5)  # 5 minutes in the past
        )
        
        # Visit the verification URL
        verify_url = reverse('waap:login_verify', kwargs={'token': expired_token.token})
        response = self.client.get(verify_url)
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_error.html')
        self.assertContains(response, 'This login link has expired')
        
        # Check that the user is not authenticated
        self.assertNotIn('waap_authenticated_user_id', self.client.session)
    
    def test_login_verify_used_token(self):
        """Test verifying a token that has already been used."""
        # Create a used token
        used_token = OneTimeToken.objects.create(
            email=self.test_email,
            token="used-token",
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True
        )
        
        # Visit the verification URL
        verify_url = reverse('waap:login_verify', kwargs={'token': used_token.token})
        response = self.client.get(verify_url)
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_error.html')
        self.assertContains(response, 'This login link has already been used')
        
        # Check that the user is not authenticated
        self.assertNotIn('waap_authenticated_user_id', self.client.session)
    
    def test_logout(self):
        """Test logging out."""
        # First, log in
        token = OneTimeToken.create_for_email(self.test_email)
        verify_url = reverse('waap:login_verify', kwargs={'token': token.token})
        self.client.get(verify_url)
        
        # Check that the user is authenticated
        self.assertIn('waap_authenticated_user_id', self.client.session)
        
        # Now, log out
        logout_url = reverse('waap:logout')
        response = self.client.get(logout_url)
        
        # Check that the response is a redirect to the job posting list
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('waap:job_posting_list'), response.url)
        
        # Check that the user is no longer authenticated
        self.assertNotIn('waap_authenticated_user_id', self.client.session)


class LoginRequiredTest(TestCase):
    """Test the login_required decorator."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.test_email = "test.user@government.ca"
        self.user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=self.test_email,
            department="Information Technology"
        )
        
        # Create a department for job posting
        self.department = Department.objects.create(name="Information Technology")
    
    def test_login_required_redirect(self):
        """Test that protected views redirect to login when not authenticated."""
        # We'll use a view that requires login (we'll need to create this view)
        # For now, we'll just check that the login_required decorator works as expected
        
        # Create a session to simulate a logged-in user
        session = self.client.session
        session['waap_authenticated_user_id'] = self.user.id
        session.save()
        
        # Now the user should be authenticated
        response = self.client.get(reverse('waap:index'))
        self.assertEqual(response.status_code, 302)  # Redirect to job_posting_list
        
        # Clear the session to simulate a logged-out user
        session = self.client.session
        if 'waap_authenticated_user_id' in session:
            del session['waap_authenticated_user_id']
        session.save()
        
        # Now the user should not be authenticated
        # If we had a protected view, it would redirect to login
        response = self.client.get(reverse('waap:job_posting_create'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('login', response.url)


class JobPostingCreationTest(TestCase):
    """Test job posting creation functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.test_email = "test.user@government.ca"
        self.user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=self.test_email,
            department="Information Technology"
        )
        
        # Create a department for job posting
        self.department = Department.objects.create(name="Information Technology")
        
        # Create a session to simulate a logged-in user
        session = self.client.session
        session['waap_authenticated_user_id'] = self.user.id
        session.save()
    
    def test_job_posting_create_view_get(self):
        """Test that the job posting create view loads correctly."""
        response = self.client.get(reverse('waap:job_posting_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_create.html')
        self.assertIn('departments', response.context)
        self.assertIn('classification_choices', response.context)
        self.assertIn('language_profile_choices', response.context)
    
    def test_job_posting_create_view_post(self):
        """Test that a job posting can be created by an authenticated user."""
        # Create a job posting
        response = self.client.post(reverse('waap:job_posting_create'), {
            'job_title': 'Software Developer',
            'department': self.department.id,
            'location': 'Ottawa, ON',
            'classification': 'PERMANENT',
            'language_profile': 'BILINGUAL',
            'contact_email': 'hr@example.ca',
            'alternation_criteria': '{"experience": "3+ years", "skills": ["Python", "Django"]}',
        })
        
        # Check that the job posting was created
        self.assertEqual(JobPosting.objects.count(), 1)
        job_posting = JobPosting.objects.first()
        self.assertEqual(job_posting.job_title, 'Software Developer')
        self.assertEqual(job_posting.department, self.department)
        self.assertEqual(job_posting.location, 'Ottawa, ON')
        self.assertEqual(job_posting.classification, 'PERMANENT')
        self.assertEqual(job_posting.language_profile, 'BILINGUAL')
        self.assertEqual(job_posting.contact_email, 'hr@example.ca')
        self.assertEqual(job_posting.alternation_criteria['experience'], '3+ years')
        self.assertIn('Python', job_posting.alternation_criteria['skills'])
        
        # Check that the creator is set correctly
        self.assertEqual(job_posting.creator, self.user)
        
        # Check that the response is a redirect to the job posting detail page
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('waap:job_posting_detail', kwargs={'pk': job_posting.id}))
    
    def test_job_posting_create_view_post_invalid(self):
        """Test that invalid form data is handled correctly."""
        # Try to create a job posting with missing required fields
        response = self.client.post(reverse('waap:job_posting_create'), {
            'job_title': 'Software Developer',
            # Missing department
            'location': 'Ottawa, ON',
            'classification': 'PERMANENT',
            'language_profile': 'BILINGUAL',
        })
        
        # Check that the job posting was not created
        self.assertEqual(JobPosting.objects.count(), 0)
        
        # Check that the response contains an error message
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_create.html')
        self.assertIn('error_message', response.context)
    
    def test_job_posting_detail_view(self):
        """Test that the job posting detail view loads correctly."""
        # Create a job posting
        job_posting = JobPosting.objects.create(
            job_title='Software Developer',
            department=self.department,
            location='Ottawa, ON',
            classification='PERMANENT',
            language_profile='BILINGUAL',
            contact_email='hr@example.ca',
            creator=self.user,
        )
        
        # Get the job posting detail page
        response = self.client.get(reverse('waap:job_posting_detail', kwargs={'pk': job_posting.id}))
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_detail.html')
        self.assertEqual(response.context['job_posting'], job_posting)
        self.assertTrue(response.context['is_owner'])


class JobPostingDeletionTest(TestCase):
    """Test job posting deletion functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.test_email = "test.user@government.ca"
        self.user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=self.test_email,
            department="Information Technology"
        )
        
        # Create another user who is not the creator
        self.other_user = WaapUser.objects.create(
            first_name="Other",
            last_name="User",
            email="other.user@government.ca",
            department="Human Resources"
        )
        
        # Create a department for job posting
        self.department = Department.objects.create(name="Information Technology")
        
        # Create a job posting
        self.job_posting = JobPosting.objects.create(
            job_title='Software Developer',
            department=self.department,
            location='Ottawa, ON',
            classification='PERMANENT',
            language_profile='BILINGUAL',
            contact_email='hr@example.ca',
            creator=self.user,
        )
    
    def test_job_posting_delete_request_view_owner(self):
        """Test that the job posting delete request view works for the owner."""
        # Create a session to simulate a logged-in user (the owner)
        session = self.client.session
        session['waap_authenticated_user_id'] = self.user.id
        session.save()
        
        # Get the job posting delete request page
        response = self.client.get(reverse('waap:job_posting_delete_request', kwargs={'pk': self.job_posting.id}))
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_request.html')
        self.assertEqual(response.context['job_posting'], self.job_posting)
        self.assertEqual(response.context['user'], self.user)
        self.assertNotIn('error_message', response.context)
    
    def test_job_posting_delete_request_view_non_owner(self):
        """Test that the job posting delete request view shows an error for non-owners."""
        # Create a session to simulate a logged-in user (not the owner)
        session = self.client.session
        session['waap_authenticated_user_id'] = self.other_user.id
        session.save()
        
        # Get the job posting delete request page
        response = self.client.get(reverse('waap:job_posting_delete_request', kwargs={'pk': self.job_posting.id}))
        
        # Check that the response contains an error message
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_request.html')
        self.assertIn('error_message', response.context)
    
    def test_job_posting_delete_request_view_post(self):
        """Test that a deletion email is sent when the owner requests deletion."""
        # Create a session to simulate a logged-in user (the owner)
        session = self.client.session
        session['waap_authenticated_user_id'] = self.user.id
        session.save()
        
        # Post to the job posting delete request page
        response = self.client.post(reverse('waap:job_posting_delete_request', kwargs={'pk': self.job_posting.id}))
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_request_success.html')
        
        # Check that a deletion token was generated
        self.job_posting.refresh_from_db()
        self.assertIsNotNone(self.job_posting.deletion_token)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn('WAAP Job Posting Deletion Link', mail.outbox[0].subject)
    
    def test_job_posting_delete_confirm_view_get(self):
        """Test that the job posting delete confirm view loads correctly."""
        # Set a deletion token
        self.job_posting.deletion_token = 'test-deletion-token'
        self.job_posting.save()
        
        # Get the job posting delete confirm page
        response = self.client.get(reverse('waap:job_posting_delete_confirm', kwargs={'token': 'test-deletion-token'}))
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_confirm.html')
        self.assertEqual(response.context['job_posting'], self.job_posting)
    
    def test_job_posting_delete_confirm_view_post(self):
        """Test that a job posting can be deleted with a valid token."""
        # Set a deletion token
        self.job_posting.deletion_token = 'test-deletion-token'
        self.job_posting.save()
        
        # Post to the job posting delete confirm page
        response = self.client.post(reverse('waap:job_posting_delete_confirm', kwargs={'token': 'test-deletion-token'}))
        
        # Check that the job posting was deleted
        self.assertEqual(JobPosting.objects.count(), 0)
        
        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_success.html')
        self.assertEqual(response.context['job_title'], 'Software Developer')
    
    def test_job_posting_delete_confirm_view_invalid_token(self):
        """Test that an invalid token is handled correctly."""
        # Post to the job posting delete confirm page with an invalid token
        response = self.client.get(reverse('waap:job_posting_delete_confirm', kwargs={'token': 'invalid-token'}))
        
        # Check that the job posting was not deleted
        self.assertEqual(JobPosting.objects.count(), 1)
        
        # Check that the response contains an error message
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_confirm.html')
        self.assertIn('error_message', response.context)
