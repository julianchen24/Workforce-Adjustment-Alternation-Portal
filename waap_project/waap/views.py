from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.views.decorators.http import require_http_methods

from .models import WaapUser, OneTimeToken, Department, JobPosting
import re
import json
import secrets
from datetime import datetime

def index(request):
    """Home page view for the WAAP application."""
    return redirect('waap:job_posting_list')

# Session key for authentication
AUTH_SESSION_KEY = 'waap_authenticated_user_id'

def is_authenticated(request):
    """Check if the user is authenticated."""
    return AUTH_SESSION_KEY in request.session

def get_authenticated_user(request):
    """Get the authenticated user from the session."""
    if not is_authenticated(request):
        return None
    
    user_id = request.session.get(AUTH_SESSION_KEY)
    try:
        return WaapUser.objects.get(id=user_id)
    except WaapUser.DoesNotExist:
        # Clear invalid session
        request.session.pop(AUTH_SESSION_KEY, None)
        return None

def login_required(view_func):
    """Decorator to require login for a view."""
    def wrapper(request, *args, **kwargs):
        if not is_authenticated(request):
            # Store the original URL to redirect back after login
            request.session['next_url'] = request.get_full_path()
            return redirect('waap:login_request')
        return view_func(request, *args, **kwargs)
    return wrapper

def is_valid_government_email(email):
    """Check if the email is a valid government email."""
    # This is a simple check for .ca domain
    # In a real application, you might want to check for specific government domains
    return bool(re.search(r'\.ca$', email))

def send_login_email(request, email, token):
    """Send a login email with the one-time token."""
    # Construct the login URL with the token
    login_url = request.build_absolute_uri(
        reverse('waap:login_verify', kwargs={'token': token.token})
    )
    
    # Render the email templates
    subject = 'Your WAAP Login Link'
    html_content = render_to_string('waap/email/login_link.html', {
        'login_url': login_url,
    })
    text_content = render_to_string('waap/email/login_link.txt', {
        'login_url': login_url,
    })
    
    # Create the email message
    email_message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    email_message.attach_alternative(html_content, "text/html")
    
    # Send the email
    return email_message.send()

@require_http_methods(["GET", "POST"])
def login_request(request):
    """View for requesting a one-time login link."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        # Validate the email
        if not email:
            return render(request, 'waap/login_request.html', {
                'error_message': 'Please enter your email address.'
            })
        
        if not is_valid_government_email(email):
            return render(request, 'waap/login_request.html', {
                'error_message': 'Please enter a valid government email address ending with .ca'
            })
        
        # Create a new token for the email
        token = OneTimeToken.create_for_email(email)
        
        # Send the login email
        try:
            send_login_email(request, email, token)
            return render(request, 'waap/login_request_success.html', {'email': email})
        except Exception as e:
            # Log the error in a real application
            return render(request, 'waap/login_request.html', {
                'error_message': 'Failed to send login email. Please try again later.'
            })
    
    return render(request, 'waap/login_request.html')

@require_http_methods(["GET"])
def login_verify(request, token):
    """View for verifying a one-time login token."""
    # Find the token in the database
    try:
        token_obj = OneTimeToken.objects.get(token=token)
    except OneTimeToken.DoesNotExist:
        return render(request, 'waap/login_error.html', {
            'error_message': 'Invalid login link.'
        })
    
    # Check if the token is valid
    if not token_obj.is_valid:
        if token_obj.is_used:
            error_message = 'This login link has already been used.'
        else:
            error_message = 'This login link has expired.'
        
        return render(request, 'waap/login_error.html', {
            'error_message': error_message
        })
    
    # Mark the token as used
    token_obj.is_used = True
    token_obj.save()
    
    # Find or create the user
    try:
        user = WaapUser.objects.get(email=token_obj.email)
    except WaapUser.DoesNotExist:
        # In a real application, you might want to redirect to a registration page
        # or create a placeholder user
        return render(request, 'waap/login_error.html', {
            'error_message': 'No user found with this email address.'
        })
    
    # Set the user as authenticated in the session
    request.session[AUTH_SESSION_KEY] = user.id
    
    # Redirect to the next URL if available, otherwise to the success page
    next_url = request.session.pop('next_url', None)
    if next_url:
        return redirect(next_url)
    
    return render(request, 'waap/login_success.html', {'user': user})

@login_required
def logout(request):
    """View for logging out."""
    if AUTH_SESSION_KEY in request.session:
        del request.session[AUTH_SESSION_KEY]
    
    return redirect('waap:job_posting_list')


@login_required
def job_posting_create(request):
    """View for creating a new job posting. Requires authentication."""
    # Get the authenticated user
    user = get_authenticated_user(request)
    if not user:
        return redirect('waap:login_request')
    
    # Get all departments for the form
    departments = Department.objects.all()
    
    if request.method == 'POST':
        # Process the form submission
        try:
            # Get form data
            job_title = request.POST.get('job_title')
            department_id = request.POST.get('department')
            location = request.POST.get('location')
            classification = request.POST.get('classification')
            language_profile = request.POST.get('language_profile')
            contact_email = request.POST.get('contact_email')
            expiration_date_str = request.POST.get('expiration_date')
            alternation_criteria_str = request.POST.get('alternation_criteria')
            
            # Validate required fields
            if not (job_title and department_id and location and classification and language_profile):
                return render(request, 'waap/job_posting_create.html', {
                    'error_message': 'Please fill in all required fields.',
                    'departments': departments,
                    'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
                    'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
                })
            
            # Get the department
            try:
                department = Department.objects.get(id=department_id)
            except Department.DoesNotExist:
                return render(request, 'waap/job_posting_create.html', {
                    'error_message': 'Invalid department selected.',
                    'departments': departments,
                    'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
                    'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
                })
            
            # Parse expiration date if provided
            expiration_date = None
            if expiration_date_str:
                try:
                    expiration_date = timezone.make_aware(
                        datetime.strptime(expiration_date_str, '%Y-%m-%d')
                    )
                except ValueError:
                    return render(request, 'waap/job_posting_create.html', {
                        'error_message': 'Invalid expiration date format.',
                        'departments': departments,
                        'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
                        'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
                    })
            
            # Parse alternation criteria if provided
            alternation_criteria = {}
            if alternation_criteria_str:
                try:
                    alternation_criteria = json.loads(alternation_criteria_str)
                except json.JSONDecodeError:
                    return render(request, 'waap/job_posting_create.html', {
                        'error_message': 'Invalid JSON format for alternation criteria.',
                        'departments': departments,
                        'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
                        'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
                    })
            
            # Create the job posting
            job_posting = JobPosting(
                job_title=job_title,
                department=department,
                location=location,
                classification=classification,
                language_profile=language_profile,
                contact_email=contact_email,
                alternation_criteria=alternation_criteria,
                creator=user,  # Set the creator to the authenticated user
            )
            
            if expiration_date:
                job_posting.expiration_date = expiration_date
            
            job_posting.save()
            
            # Redirect to the job posting detail page
            return redirect('waap:job_posting_detail', pk=job_posting.id)
            
        except Exception as e:
            # Log the error in a real application
            return render(request, 'waap/job_posting_create.html', {
                'error_message': f'An error occurred: {str(e)}',
                'departments': departments,
                'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
                'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
            })
    
    # Render the form for GET requests
    return render(request, 'waap/job_posting_create.html', {
        'departments': departments,
        'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
        'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
    })

def send_deletion_email(request, job_posting, user):
    """Send a deletion email with the job posting's deletion token."""
    # Construct the deletion URL with the token
    deletion_url = request.build_absolute_uri(
        reverse('waap:job_posting_delete_confirm', kwargs={'token': job_posting.deletion_token})
    )
    
    # Render the email templates
    subject = 'WAAP Job Posting Deletion Link'
    html_content = render_to_string('waap/email/deletion_link.html', {
        'job_posting': job_posting,
        'deletion_url': deletion_url,
    })
    text_content = render_to_string('waap/email/deletion_link.txt', {
        'job_posting': job_posting,
        'deletion_url': deletion_url,
    })
    
    # Create the email message
    email_message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email_message.attach_alternative(html_content, "text/html")
    
    # Send the email
    return email_message.send()


@login_required
def job_posting_detail(request, pk):
    """View for displaying a job posting's details."""
    # Get the job posting
    job_posting = get_object_or_404(JobPosting, pk=pk)
    
    # Get the authenticated user
    user = get_authenticated_user(request)
    
    # Check if the user is the creator of the job posting
    is_owner = user and job_posting.creator and user.id == job_posting.creator.id
    
    # Render the template
    return render(request, 'waap/job_posting_detail.html', {
        'job_posting': job_posting,
        'is_owner': is_owner,
    })


@login_required
def job_posting_delete_request(request, pk):
    """View for requesting a deletion link for a job posting."""
    # Get the job posting
    job_posting = get_object_or_404(JobPosting, pk=pk)
    
    # Get the authenticated user
    user = get_authenticated_user(request)
    
    # Check if the user is the creator of the job posting
    if not user or not job_posting.creator or user.id != job_posting.creator.id:
        return render(request, 'waap/job_posting_delete_request.html', {
            'error_message': 'You are not authorized to delete this job posting.',
            'job_posting': job_posting,
            'user': user,
        })
    
    if request.method == 'POST':
        # Generate a new deletion token
        job_posting.deletion_token = secrets.token_urlsafe(32)
        job_posting.save()
        
        # Send the deletion email
        try:
            send_deletion_email(request, job_posting, user)
            return render(request, 'waap/job_posting_delete_request_success.html', {
                'job_posting': job_posting,
                'email': user.email,
            })
        except Exception as e:
            # Log the error in a real application
            return render(request, 'waap/job_posting_delete_request.html', {
                'error_message': 'Failed to send deletion email. Please try again later.',
                'job_posting': job_posting,
                'user': user,
            })
    
    # Render the form for GET requests
    return render(request, 'waap/job_posting_delete_request.html', {
        'job_posting': job_posting,
        'user': user,
    })


def job_posting_delete_confirm(request, token):
    """View for confirming the deletion of a job posting using a token."""
    # Find the job posting with the given deletion token
    try:
        job_posting = JobPosting.objects.get(deletion_token=token)
    except JobPosting.DoesNotExist:
        return render(request, 'waap/job_posting_delete_confirm.html', {
            'error_message': 'Invalid deletion link.',
        })
    
    if request.method == 'POST':
        # Store the job title for the success message
        job_title = job_posting.job_title
        
        # Delete the job posting
        job_posting.delete()
        
        # Render the success template
        return render(request, 'waap/job_posting_delete_success.html', {
            'job_title': job_title,
        })
    
    # Render the confirmation template for GET requests
    return render(request, 'waap/job_posting_delete_confirm.html', {
        'job_posting': job_posting,
    })


class UserListView(ListView):
    """View to display all users in the system."""
    model = WaapUser
    template_name = 'waap/user_list.html'
    context_object_name = 'users'


class JobPostingListView(ListView):
    """View to display all job postings in the system."""
    model = JobPosting
    template_name = 'waap/job_posting_list.html'
    context_object_name = 'job_postings'
    
    def get_queryset(self):
        """Return only active job postings."""
        return JobPosting.objects.filter(expiration_date__gte=timezone.now()).order_by('-posting_date')
