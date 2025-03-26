from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core import mail
from django.contrib.auth.models import User
from django.core.management import call_command
from io import StringIO
from datetime import timedelta
from unittest.mock import patch, MagicMock

from .models import WaapUser, Department, JobPosting, OneTimeToken, ContactMessage

class IntegrationTest(TestCase):
    """
    Integration tests for the WAAP application.
    
    These tests simulate the entire workflow of the application:
    1. User authentication
    2. Job posting creation
    3. Public browsing and filtering
    4. Contact form functionality
    5. Deletion process
    6. Auto-expiration functionality
    """
    
    def setUp(self):
        """Set up test data."""
        # Create departments
        self.department_it = Department.objects.create(name="Information Technology")
        self.department_hr = Department.objects.create(name="Human Resources")
        
        # Create admin user for moderation tests
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        
        # Create a client
        self.client = Client()
        
        # URLs for common actions
        self.login_request_url = reverse('waap:login_request')
        self.public_job_postings_url = reverse('waap:public_job_postings')
    
    def test_end_to_end_workflow(self):
        """
        Test the entire workflow from login to job posting creation, 
        browsing, contact, and deletion.
        """
        # Step 1: Create a user first (in a real scenario, this might be done by an admin)
        user_email = "test.user@government.ca"
        user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=user_email,
            department="Information Technology"
        )
        
        # Step 2: User requests a one-time login link
        response = self.client.post(self.login_request_url, {'email': user_email})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_request_success.html')
        
        # Check that a token was created and an email was sent
        self.assertEqual(OneTimeToken.objects.filter(email=user_email).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user_email])
        
        # Extract the token from the email
        token = OneTimeToken.objects.get(email=user_email)
        
        # Step 3: User clicks the login link and gets authenticated
        verify_url = reverse('waap:login_verify', kwargs={'token': token.token})
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/login_success.html')
        
        # Check that the user is authenticated in the session
        self.assertEqual(self.client.session['waap_authenticated_user_id'], user.id)
        
        # Step 3: User creates a job posting
        job_posting_data = {
            'job_title': 'Software Developer',
            'department': self.department_it.id,
            'location': 'Ottawa, ON',
            'classification': 'PERMANENT',
            'language_profile': 'BILINGUAL',
            'contact_email': user_email,
            'alternation_criteria': '{"experience": "3+ years", "skills": ["Python", "Django"]}',
        }
        
        response = self.client.post(reverse('waap:job_posting_create'), job_posting_data)
        self.assertEqual(response.status_code, 302)  # Redirect to job posting detail
        
        # Check that the job posting was created
        self.assertEqual(JobPosting.objects.count(), 1)
        job_posting = JobPosting.objects.first()
        self.assertEqual(job_posting.job_title, 'Software Developer')
        self.assertEqual(job_posting.creator, user)
        
        # Step 4: Public user browses job postings
        # First, log out the current user
        self.client.get(reverse('waap:logout'))
        
        # Browse the public job postings page
        response = self.client.get(self.public_job_postings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Developer')
        
        # Test filtering
        response = self.client.get(
            self.public_job_postings_url,
            {'department': self.department_it.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertIn('Software Developer', data['html'])
        
        # Step 5: Public user contacts the job posting owner
        with patch('captcha.fields.ReCaptchaField.clean') as mock_clean:
            # Mock the CAPTCHA validation to pass
            mock_clean.return_value = 'PASSED'
            
            contact_data = {
                'sender_name': 'John Doe',
                'sender_email': 'john.doe@example.com',
                'message': 'I am interested in this position. Please contact me.',
                'captcha': 'PASSED',
            }
            
            response = self.client.post(reverse('waap:contact_form', kwargs={'pk': job_posting.id}), contact_data)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'waap/contact_success.html')
        
        # Check that a contact message was created and an email was sent
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 2)  # First email was for login
        self.assertEqual(mail.outbox[1].to, [user_email])
        
        # Step 6: User logs back in and requests deletion of their job posting
        # First, create a new token for the user
        token = OneTimeToken.create_for_email(user_email)
        
        # User clicks the login link
        verify_url = reverse('waap:login_verify', kwargs={'token': token.token})
        self.client.get(verify_url)
        
        # User requests deletion
        response = self.client.post(reverse('waap:job_posting_delete_request', kwargs={'pk': job_posting.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_request_success.html')
        
        # Check that a deletion email was sent
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[2].to, [user_email])
        
        # Extract the deletion token from the job posting
        job_posting.refresh_from_db()
        deletion_token = job_posting.deletion_token
        
        # Step 7: User confirms deletion
        response = self.client.post(reverse('waap:job_posting_delete_confirm', kwargs={'token': deletion_token}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'waap/job_posting_delete_success.html')
        
        # Check that the job posting was deleted
        self.assertEqual(JobPosting.objects.count(), 0)

    def test_admin_moderation_workflow(self):
        """
        Test the admin moderation workflow.
        """
        # Create a user
        user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email="test.user@government.ca",
            department="Information Technology"
        )
        
        # Create a job posting
        job_posting = JobPosting.objects.create(
            job_title='Software Developer',
            department=self.department_it,
            location='Ottawa, ON',
            classification='PERMANENT',
            language_profile='BILINGUAL',
            contact_email='test.user@government.ca',
            creator=user,
            expiration_date=timezone.now() + timedelta(days=30),
            moderation_status='APPROVED'
        )
        
        # Log in as admin
        admin_client = Client()
        admin_client.login(username='admin', password='adminpassword')
        
        # Flag the job posting for review
        admin_url = reverse('admin:waap_jobposting_changelist')
        data = {
            'action': 'flag_for_review',
            '_selected_action': [job_posting.id]
        }
        response = admin_client.post(admin_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was flagged
        job_posting.refresh_from_db()
        self.assertEqual(job_posting.moderation_status, 'FLAGGED')
        
        # Check that the flagged job posting is not visible on the public page
        response = self.client.get(self.public_job_postings_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Software Developer')
        
        # Check that the contact form shows an error for flagged postings
        response = self.client.get(reverse('waap:contact_form', kwargs={'pk': job_posting.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This job posting is currently under review')
        
        # Approve the job posting
        data = {
            'action': 'approve_posting',
            '_selected_action': [job_posting.id]
        }
        response = admin_client.post(admin_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was approved
        job_posting.refresh_from_db()
        self.assertEqual(job_posting.moderation_status, 'APPROVED')
        
        # Check that the approved job posting is visible on the public page
        response = self.client.get(self.public_job_postings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Developer')

    def test_auto_expiration_workflow(self):
        """
        Test the auto-expiration workflow.
        """
        # Create a user
        user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email="test.user@government.ca",
            department="Information Technology"
        )
        
        # Create an active job posting
        active_job = JobPosting.objects.create(
            job_title="Active Position",
            department=self.department_it,
            location="Ottawa, ON",
            classification="PERMANENT",
            language_profile="BILINGUAL",
            contact_email="active@example.ca",
            creator=user,
            expiration_date=timezone.now() + timedelta(days=15)
        )
        
        # Create an expired job posting
        expired_job = JobPosting.objects.create(
            job_title="Expired Position",
            department=self.department_it,
            location="Toronto, ON",
            classification="CONTRACT",
            language_profile="ENGLISH",
            contact_email="expired@example.ca",
            creator=user,
            expiration_date=timezone.now() - timedelta(days=5)
        )
        
        # Run the expire_job_postings command
        out = StringIO()
        call_command('expire_job_postings', stdout=out)
        output = out.getvalue()
        
        # Check the command output
        self.assertIn("Found 1 expired job postings", output)
        self.assertIn(f"Anonymizing job posting: {expired_job.job_title}", output)
        
        # Check that the expired job posting was anonymized
        expired_job.refresh_from_db()
        self.assertIsNone(expired_job.contact_email)
        
        # Check that the active job posting was not anonymized
        active_job.refresh_from_db()
        self.assertEqual(active_job.contact_email, "active@example.ca")
        
        # Check that only the active job posting is visible on the public page
        response = self.client.get(self.public_job_postings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Position')
        self.assertNotContains(response, 'Expired Position')

    def test_integrated_workflow_with_moderation_and_expiration(self):
        """
        Test the integrated workflow with moderation and expiration.
        """
        # Step 1: Create a user first and then log in
        user_email = "test.user@government.ca"
        user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email=user_email,
            department="Information Technology"
        )
        
        # Create a token and log in
        token = OneTimeToken.create_for_email(user_email)
        verify_url = reverse('waap:login_verify', kwargs={'token': token.token})
        self.client.get(verify_url)
        
        # Step 2: User creates a job posting
        job_posting_data = {
            'job_title': 'Software Developer',
            'department': self.department_it.id,
            'location': 'Ottawa, ON',
            'classification': 'PERMANENT',
            'language_profile': 'BILINGUAL',
            'contact_email': user_email,
            'alternation_criteria': '{"experience": "3+ years", "skills": ["Python", "Django"]}',
        }
        
        self.client.post(reverse('waap:job_posting_create'), job_posting_data)
        job_posting = JobPosting.objects.first()
        
        # Step 3: Admin flags the job posting for review
        admin_client = Client()
        admin_client.login(username='admin', password='adminpassword')
        admin_url = reverse('admin:waap_jobposting_changelist')
        data = {
            'action': 'flag_for_review',
            '_selected_action': [job_posting.id]
        }
        admin_client.post(admin_url, data, follow=True)
        
        # Step 4: Public user tries to contact but gets an error
        with patch('captcha.fields.ReCaptchaField.clean') as mock_clean:
            mock_clean.return_value = 'PASSED'
            
            contact_data = {
                'sender_name': 'John Doe',
                'sender_email': 'john.doe@example.com',
                'message': 'I am interested in this position. Please contact me.',
                'captcha': 'PASSED',
            }
            
            response = self.client.get(reverse('waap:contact_form', kwargs={'pk': job_posting.id}))
            self.assertContains(response, 'This job posting is currently under review')
        
        # Step 5: Admin approves the job posting
        data = {
            'action': 'approve_posting',
            '_selected_action': [job_posting.id]
        }
        admin_client.post(admin_url, data, follow=True)
        
        # Step 6: Public user successfully contacts the job posting owner
        with patch('captcha.fields.ReCaptchaField.clean') as mock_clean:
            mock_clean.return_value = 'PASSED'
            
            response = self.client.post(reverse('waap:contact_form', kwargs={'pk': job_posting.id}), contact_data)
            self.assertTemplateUsed(response, 'waap/contact_success.html')
        
        # Step 7: Set the job posting as expired
        job_posting.expiration_date = timezone.now() - timedelta(days=1)
        job_posting.save()
        
        # Step 8: Run the expire_job_postings command
        call_command('expire_job_postings')
        
        # Step 9: Check that the job posting was anonymized
        job_posting.refresh_from_db()
        self.assertIsNone(job_posting.contact_email)
        
        # Step 10: Check that the expired job posting is not visible on the public page
        response = self.client.get(self.public_job_postings_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Software Developer')
