from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

from .models import Department, JobPosting, WaapUser, ContactMessage


class AdminModerationTest(TestCase):
    """Test the admin moderation functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create a superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        
        # Create a department
        self.department = Department.objects.create(name="Information Technology")
        
        # Create a user
        self.waap_user = WaapUser.objects.create(
            first_name="Test",
            last_name="User",
            email="test.user@government.ca",
            department="Information Technology"
        )
        
        # Create job postings with different statuses
        # Active, approved job posting
        self.approved_job = JobPosting.objects.create(
            job_title="Approved Position",
            department=self.department,
            location="Ottawa, ON",
            classification="PERMANENT",
            language_profile="BILINGUAL",
            contact_email="approved@example.ca",
            creator=self.waap_user,
            expiration_date=timezone.now() + timedelta(days=30),
            moderation_status="APPROVED"
        )
        
        # Active, flagged job posting
        self.flagged_job = JobPosting.objects.create(
            job_title="Flagged Position",
            department=self.department,
            location="Toronto, ON",
            classification="CONTRACT",
            language_profile="ENGLISH",
            contact_email="flagged@example.ca",
            creator=self.waap_user,
            expiration_date=timezone.now() + timedelta(days=30),
            moderation_status="FLAGGED"
        )
        
        # Active, inappropriate job posting
        self.inappropriate_job = JobPosting.objects.create(
            job_title="Inappropriate Position",
            department=self.department,
            location="Montreal, QC",
            classification="TEMPORARY",
            language_profile="FRENCH",
            contact_email="inappropriate@example.ca",
            creator=self.waap_user,
            expiration_date=timezone.now() + timedelta(days=30),
            moderation_status="INAPPROPRIATE"
        )
        
        # Expired job posting
        self.expired_job = JobPosting.objects.create(
            job_title="Expired Position",
            department=self.department,
            location="Vancouver, BC",
            classification="CASUAL",
            language_profile="ENGLISH_PREFERRED",
            contact_email="expired@example.ca",
            creator=self.waap_user,
            expiration_date=timezone.now() - timedelta(days=1),
            moderation_status="APPROVED"
        )
        
        # Create a client and log in as admin
        self.client = Client()
        self.client.login(username='admin', password='adminpassword')
        
        # URLs for admin actions
        self.admin_job_posting_url = reverse('admin:waap_jobposting_changelist')
        self.admin_job_posting_change_url = reverse('admin:waap_jobposting_change', args=[self.approved_job.id])
    
    def test_admin_job_posting_list(self):
        """Test that the admin job posting list shows all job postings."""
        response = self.client.get(self.admin_job_posting_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that all job postings are listed
        self.assertContains(response, "Approved Position")
        self.assertContains(response, "Flagged Position")
        self.assertContains(response, "Inappropriate Position")
        self.assertContains(response, "Expired Position")
    
    def test_admin_job_posting_change(self):
        """Test that the admin job posting change page shows all fields."""
        response = self.client.get(self.admin_job_posting_change_url)
        self.assertEqual(response.status_code, 200)
        
        # Check that moderation fields are included
        self.assertContains(response, "Moderation status")
        self.assertContains(response, "Moderation notes")
    
    def test_admin_mark_as_inappropriate_action(self):
        """Test the 'mark as inappropriate' admin action."""
        # Get the current count of log entries
        initial_log_count = LogEntry.objects.count()
        
        # Perform the action
        data = {
            'action': 'mark_as_inappropriate',
            '_selected_action': [self.approved_job.id]
        }
        response = self.client.post(self.admin_job_posting_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was marked as inappropriate
        self.approved_job.refresh_from_db()
        self.assertEqual(self.approved_job.moderation_status, "INAPPROPRIATE")
        
        # Check that the moderation date and by fields were updated
        self.assertIsNotNone(self.approved_job.moderation_date)
        self.assertEqual(self.approved_job.moderation_by, "admin")
        
        # Check that at least one log entry was created
        self.assertGreater(LogEntry.objects.count(), initial_log_count)
        log_entry = LogEntry.objects.latest('id')
        self.assertEqual(log_entry.object_id, str(self.approved_job.id))
        self.assertEqual(log_entry.user, self.admin_user)
    
    def test_admin_flag_for_review_action(self):
        """Test the 'flag for review' admin action."""
        # Perform the action
        data = {
            'action': 'flag_for_review',
            '_selected_action': [self.approved_job.id]
        }
        response = self.client.post(self.admin_job_posting_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was flagged for review
        self.approved_job.refresh_from_db()
        self.assertEqual(self.approved_job.moderation_status, "FLAGGED")
    
    def test_admin_approve_posting_action(self):
        """Test the 'approve posting' admin action."""
        # Perform the action
        data = {
            'action': 'approve_posting',
            '_selected_action': [self.flagged_job.id]
        }
        response = self.client.post(self.admin_job_posting_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was approved
        self.flagged_job.refresh_from_db()
        self.assertEqual(self.flagged_job.moderation_status, "APPROVED")
    
    def test_admin_remove_posting_action(self):
        """Test the 'remove posting' admin action."""
        # Perform the action
        data = {
            'action': 'remove_posting',
            '_selected_action': [self.approved_job.id]
        }
        response = self.client.post(self.admin_job_posting_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was removed
        self.approved_job.refresh_from_db()
        self.assertEqual(self.approved_job.moderation_status, "REMOVED")
    
    def test_admin_save_moderation_status(self):
        """Test saving moderation status through the admin form."""
        # Get the current count of log entries
        initial_log_count = LogEntry.objects.count()
        
        # Update the job posting with a new moderation status and notes
        data = {
            'job_title': self.approved_job.job_title,
            'department': self.approved_job.department.id,
            'location': self.approved_job.location,
            'classification': self.approved_job.classification,
            'language_profile': self.approved_job.language_profile,
            'contact_email': self.approved_job.contact_email,
            'expiration_date_0': self.approved_job.expiration_date.date().strftime('%Y-%m-%d'),
            'expiration_date_1': self.approved_job.expiration_date.time().strftime('%H:%M:%S'),
            'moderation_status': 'FLAGGED',
            'moderation_notes': 'This posting needs review.',
            'alternation_criteria': '{}',
            'creator': self.waap_user.id if self.approved_job.creator else '',
            '_save': 'Save',  # This is needed to trigger the save action
        }
        response = self.client.post(self.admin_job_posting_change_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check that the job posting was updated
        self.approved_job.refresh_from_db()
        self.assertEqual(self.approved_job.moderation_status, "FLAGGED")
        self.assertEqual(self.approved_job.moderation_notes, "This posting needs review.")
        
        # Check that the moderation date and by fields were updated
        self.assertIsNotNone(self.approved_job.moderation_date)
        self.assertEqual(self.approved_job.moderation_by, "admin")
        
        # Check that at least one log entry was created
        self.assertGreater(LogEntry.objects.count(), initial_log_count)
    
    def test_public_view_filters_by_moderation_status(self):
        """Test that the public view only shows approved job postings."""
        # Get the public job postings page
        response = self.client.get(reverse('waap:public_job_postings'))
        self.assertEqual(response.status_code, 200)
        
        # Check that only approved job postings are shown
        self.assertContains(response, "Approved Position")
        self.assertNotContains(response, "Flagged Position")
        self.assertNotContains(response, "Inappropriate Position")
        
        # Expired job postings should also not be shown
        self.assertNotContains(response, "Expired Position")
    
    def test_contact_form_respects_moderation_status(self):
        """Test that the contact form respects moderation status."""
        # Try to contact for an approved job posting
        response = self.client.get(reverse('waap:contact_form', kwargs={'pk': self.approved_job.id}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "This job posting is currently under review")
        
        # Try to contact for a flagged job posting
        response = self.client.get(reverse('waap:contact_form', kwargs={'pk': self.flagged_job.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This job posting is currently under review")
        
        # Try to contact for an inappropriate job posting
        response = self.client.get(reverse('waap:contact_form', kwargs={'pk': self.inappropriate_job.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This job posting is currently under review")
