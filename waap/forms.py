from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    """Form for contacting job posting owners with CAPTCHA validation."""
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    class Meta:
        model = ContactMessage
        fields = ['sender_name', 'sender_email', 'message']
        widgets = {
            'sender_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'sender_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message', 'rows': 5}),
        }
        labels = {
            'sender_name': 'Your Name',
            'sender_email': 'Your Email',
            'message': 'Message',
        }
        help_texts = {
            'sender_email': 'Your email will be shared with the job posting owner for them to respond to you.',
        }
