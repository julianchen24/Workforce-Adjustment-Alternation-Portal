from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, View
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from .models import WaapUser, OneTimeToken, Department, JobPosting, ContactMessage
from .forms import ContactForm
import re
import json
import secrets
from datetime import datetime, timedelta

def index(request):
    """Home page view for the WAAP application."""
    return redirect('waap:public_job_postings')

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
    
    return redirect('waap:public_job_postings')


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


class PublicJobPostingView(View):
    """Public view for browsing and filtering job postings."""
    
    def get(self, request):
        """Handle GET requests for the public job posting view."""
        # Check if this is an AJAX request for filtering
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.handle_ajax_filter(request)
        
        # Regular page load
        return self.render_public_page(request)
    
    def render_public_page(self, request):
        """Render the public job posting page with initial data."""
        # Get active job postings
        job_postings = JobPosting.objects.filter(
            expiration_date__gte=timezone.now()
        ).order_by('-posting_date')
        
        # Get filter options
        departments = Department.objects.all().order_by('name')
        locations = JobPosting.objects.filter(
            expiration_date__gte=timezone.now()
        ).values_list('location', flat=True).distinct().order_by('location')
        
        # Render the template
        return render(request, 'waap/public_job_postings.html', {
            'job_postings': job_postings,
            'departments': departments,
            'locations': locations,
            'classification_choices': JobPosting.CLASSIFICATION_CHOICES,
            'language_profile_choices': JobPosting.LANGUAGE_PROFILE_CHOICES,
            'view_mode': 'card',  # Default view mode
        })
    
    def handle_ajax_filter(self, request):
        """Handle AJAX requests for filtering job postings."""
        # Get filter parameters
        department_id = request.GET.get('department')
        location = request.GET.get('location')
        classification = request.GET.get('classification')
        language_profile = request.GET.get('language_profile')
        alternation_type = request.GET.get('alternation_type')
        date_posted = request.GET.get('date_posted')
        view_mode = request.GET.get('view_mode', 'card')
        
        # Start with all active job postings
        queryset = JobPosting.objects.filter(
            expiration_date__gte=timezone.now()
        )
        
        # Apply filters
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        if location:
            queryset = queryset.filter(location=location)
        
        if classification:
            queryset = queryset.filter(classification=classification)
        
        if language_profile:
            queryset = queryset.filter(language_profile=language_profile)
        
        # Filter by alternation type (seeking/offering)
        if alternation_type:
            # This assumes alternation_criteria has a 'type' field
            # Adjust as needed based on your actual data structure
            queryset = queryset.filter(alternation_criteria__type=alternation_type)
        
        # Filter by date posted
        if date_posted:
            if date_posted == '7days':
                date_threshold = timezone.now() - timedelta(days=7)
                queryset = queryset.filter(posting_date__gte=date_threshold)
            elif date_posted == '30days':
                date_threshold = timezone.now() - timedelta(days=30)
                queryset = queryset.filter(posting_date__gte=date_threshold)
        
        # Order by posting date (newest first)
        job_postings = queryset.order_by('-posting_date')
        
        # Render the appropriate template fragment based on view mode
        if view_mode == 'table':
            html = render_to_string('waap/partials/job_postings_table.html', {
                'job_postings': job_postings,
            }, request=request)
        else:  # card view
            html = render_to_string('waap/partials/job_postings_cards.html', {
                'job_postings': job_postings,
            }, request=request)
        
        # Return JSON response with the rendered HTML
        return JsonResponse({
            'html': html,
            'count': job_postings.count(),
        })


def send_contact_email(request, contact_message):
    """Send a contact email to the job posting owner."""
    job_posting = contact_message.job_posting
    
    # Get the recipient email (job posting contact email or creator's email)
    recipient_email = job_posting.contact_email
    if not recipient_email and job_posting.creator:
        recipient_email = job_posting.creator.email
    
    if not recipient_email:
        # If no recipient email is available, mark the message as not sent
        contact_message.is_sent = False
        contact_message.save()
        return False
    
    # Render the email templates
    subject = f'New Contact Message: {job_posting.job_title}'
    html_content = render_to_string('waap/email/contact_message.html', {
        'job_posting': job_posting,
        'contact_message': contact_message,
    })
    text_content = render_to_string('waap/email/contact_message.txt', {
        'job_posting': job_posting,
        'contact_message': contact_message,
    })
    
    # Create the email message
    email_message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
        reply_to=[contact_message.sender_email]  # Set reply-to as the sender's email
    )
    email_message.attach_alternative(html_content, "text/html")
    
    # Send the email
    try:
        email_message.send()
        contact_message.is_sent = True
        contact_message.save()
        return True
    except Exception as e:
        # Log the error in a real application
        contact_message.is_sent = False
        contact_message.save()
        return False


@require_http_methods(["GET", "POST"])
def contact_form(request, pk):
    """View for the contact form."""
    # Get the job posting
    job_posting = get_object_or_404(JobPosting, pk=pk)
    
    # Check if the job posting is active
    if not job_posting.is_active:
        return render(request, 'waap/contact_form.html', {
            'job_posting': job_posting,
            'error_message': 'This job posting has expired and is no longer accepting contact messages.',
        })
    
    if request.method == 'POST':
        # Process the form submission
        form = ContactForm(request.POST)
        
        if form.is_valid():
            # Create the contact message but don't save it yet
            contact_message = form.save(commit=False)
            contact_message.job_posting = job_posting
            contact_message.save()
            
            # Send the email
            email_sent = send_contact_email(request, contact_message)
            
            if email_sent:
                # Redirect to the success page
                return render(request, 'waap/contact_success.html', {
                    'job_posting': job_posting,
                })
            else:
                # Show an error message
                return render(request, 'waap/contact_form.html', {
                    'job_posting': job_posting,
                    'form': form,
                    'error_message': 'Failed to send the contact message. Please try again later.',
                })
    else:
        # Create a new form
        form = ContactForm()
    
    # Render the form
    return render(request, 'waap/contact_form.html', {
        'job_posting': job_posting,
        'form': form,
    })
