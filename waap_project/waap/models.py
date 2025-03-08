from django.db import models
from django.utils import timezone
from datetime import timedelta

class WaapUser(models.Model):
    """Basic user model for the WAAP system."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Department(models.Model):
    """Department model for job postings."""
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class JobPosting(models.Model):
    """Job posting model for the WAAP system."""
    # Classification choices
    CLASSIFICATION_CHOICES = [
        ('PERMANENT', 'Permanent'),
        ('TEMPORARY', 'Temporary'),
        ('CONTRACT', 'Contract'),
        ('CASUAL', 'Casual'),
    ]
    
    # Language profile choices
    LANGUAGE_PROFILE_CHOICES = [
        ('ENGLISH', 'English Essential'),
        ('FRENCH', 'French Essential'),
        ('BILINGUAL', 'Bilingual'),
        ('ENGLISH_PREFERRED', 'English Preferred'),
        ('FRENCH_PREFERRED', 'French Preferred'),
    ]
    
    job_title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='job_postings')
    location = models.CharField(max_length=100)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES)
    alternation_criteria = models.JSONField(default=dict, blank=True)
    language_profile = models.CharField(max_length=20, choices=LANGUAGE_PROFILE_CHOICES)
    contact_email = models.EmailField(blank=True, null=True)
    posting_date = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.job_title} - {self.department}"
    
    def save(self, *args, **kwargs):
        # If expiration_date is not set, default to 30 days from posting_date
        if not self.expiration_date:
            self.expiration_date = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if the job posting is still active."""
        return timezone.now() <= self.expiration_date
