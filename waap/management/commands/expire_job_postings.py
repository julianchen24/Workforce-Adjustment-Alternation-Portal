from django.core.management.base import BaseCommand
from django.utils import timezone
from waap.models import JobPosting
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Expires and anonymizes job postings older than 30 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the command without making any changes to the database',
        )

    def handle(self, *args, **options):
        # Get the dry-run flag from options
        dry_run = options['dry_run']
        
        # Get current time
        now = timezone.now()
        
        # Find job postings that have expired
        # Only anonymize approved or flagged postings, not those already marked as inappropriate or removed
        expired_postings = JobPosting.objects.filter(
            expiration_date__lt=now,
            moderation_status__in=['APPROVED', 'FLAGGED']
        )
        
        # Count of processed postings
        processed_count = 0
        
        self.stdout.write(f"Found {expired_postings.count()} expired job postings")
        
        # Process each expired posting
        for posting in expired_postings:
            # Check if the posting has already been anonymized
            if posting.contact_email:
                self.stdout.write(f"Anonymizing job posting: {posting.job_title} (ID: {posting.id})")
                
                if not dry_run:
                    # Anonymize the posting by removing personal identifiers
                    posting.contact_email = None
                    
                    # Save the changes
                    posting.save()
                
                processed_count += 1
            else:
                self.stdout.write(f"Job posting already anonymized: {posting.job_title} (ID: {posting.id})")
        
        # Output summary
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN: Would have anonymized {processed_count} job postings"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully anonymized {processed_count} job postings"
            ))
