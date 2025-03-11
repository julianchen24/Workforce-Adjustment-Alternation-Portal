from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid
import secrets
import hashlib

class OneTimeToken(models.Model):
    """Model for one-time login tokens."""
    token = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Token for {self.email} ({'Used' if self.is_used else 'Active'})"
    
    def save(self, *args, **kwargs):
        # Generate a secure token if not provided
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        
        # Set expiration time if not provided (default: 1 hour)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
            
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """Check if the token is still valid (not expired and not used)."""
        return not self.is_used and timezone.now() <= self.expires_at
    
    @classmethod
    def create_for_email(cls, email):
        """Create a new token for the given email."""
        token = cls(email=email)
        token.save()
        return token


class Classification(models.Model):
    """Classification model for employee groups."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Department(models.Model):
    """Department model for job postings."""
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class WaapUser(models.Model):
    """Basic user model for the WAAP system."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='users')
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    level = models.PositiveIntegerField(null=True, blank=True, help_text="Classification level (0-100, where 0 is DEV)")
    is_profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class JobPosting(models.Model):
    """Job posting model for the WAAP system."""
    # Language profile choices
    LANGUAGE_PROFILE_CHOICES = [
        ('ENGLISH', 'English Essential'),
        ('FRENCH', 'French Essential'),
        ('BILINGUAL', 'Bilingual (BBB/BBB)'),
        ('ENGLISH_PREFERRED', 'English Preferred'),
        ('FRENCH_PREFERRED', 'French Preferred'),
    ]
    
    # Moderation status choices
    MODERATION_STATUS_CHOICES = [
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged for Review'),
        ('INAPPROPRIATE', 'Marked as Inappropriate'),
        ('REMOVED', 'Removed'),
    ]
    
    job_title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='job_postings')
    location = models.CharField(max_length=100)
    classification = models.ForeignKey(Classification, on_delete=models.PROTECT, related_name='job_postings')
    level = models.PositiveIntegerField(default=0, help_text="Classification level (0-100, where 0 is DEV)")
    alternation_criteria = models.JSONField(default=dict, blank=True)
    language_profile = models.CharField(max_length=20, choices=LANGUAGE_PROFILE_CHOICES)
    contact_email = models.EmailField(blank=True, null=True)
    posting_date = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fields for tracking the creator and deletion
    creator = models.ForeignKey(WaapUser, on_delete=models.SET_NULL, null=True, related_name='job_postings')
    deletion_token = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Moderation fields
    moderation_status = models.CharField(
        max_length=20, 
        choices=MODERATION_STATUS_CHOICES,
        default='APPROVED',
        help_text="Current moderation status of the job posting"
    )
    moderation_notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Admin notes about moderation decisions"
    )
    moderation_date = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When the last moderation action was taken"
    )
    moderation_by = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Username of the admin who performed the last moderation action"
    )
    
    def __str__(self):
        return f"{self.job_title} - {self.department}"
    
    @property
    def formatted_classification(self):
        """Return the classification in the format 'EC-07' or 'EC-DEV'."""
        if self.classification:
            if self.level == 0:
                return f"{self.classification.code}-DEV"
            else:
                # Pad the level with a leading zero if it's a single digit
                padded_level = f"{self.level:02d}"
                return f"{self.classification.code}-{padded_level}"
        return None
    
    def save(self, *args, **kwargs):
        # If expiration_date is not set, default to 30 days from posting_date
        if not self.expiration_date:
            self.expiration_date = timezone.now() + timedelta(days=30)
        
        # Generate a secure deletion token if not provided
        if not self.deletion_token:
            self.deletion_token = secrets.token_urlsafe(32)
            
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if the job posting is still active."""
        return timezone.now() <= self.expiration_date


class ContactMessage(models.Model):
    """Model for storing contact messages with one-time email relay."""
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='contact_messages')
    sender_name = models.CharField(max_length=100)
    sender_email = models.EmailField()
    # Store a hashed version of the email to prevent storing the actual email directly
    sender_email_hash = models.CharField(max_length=64, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Message from {self.sender_name} to {self.job_posting.job_title}"
    
    def save(self, *args, **kwargs):
        # Generate a hash of the sender's email if not provided
        if not self.sender_email_hash and self.sender_email:
            # Use SHA-256 to hash the email
            self.sender_email_hash = hashlib.sha256(self.sender_email.encode()).hexdigest()
            
        super().save(*args, **kwargs)
