from django.contrib import admin
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from .models import WaapUser, Department, JobPosting, ContactMessage

@admin.register(WaapUser)
class WaapUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'department', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'department')
    list_filter = ('department', 'created_at')
    
    def get_queryset(self, request):
        """Override to show all users, including those with flagged postings."""
        qs = super().get_queryset(request)
        return qs


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('sender_name', 'job_posting', 'created_at', 'is_sent')
    list_filter = ('is_sent', 'created_at')
    search_fields = ('sender_name', 'message')
    readonly_fields = ('sender_name', 'sender_email', 'sender_email_hash', 'job_posting', 'message', 'created_at', 'is_sent')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'department', 'location', 'classification', 
                   'language_profile', 'posting_date', 'expiration_date', 'is_active',
                   'moderation_status', 'creator_display')
    list_filter = ('department', 'classification', 'language_profile', 'posting_date',
                  'moderation_status', 'expiration_date')
    search_fields = ('job_title', 'location', 'moderation_notes')
    readonly_fields = ('posting_date', 'created_at', 'updated_at', 'moderation_date', 'moderation_by')
    actions = ['mark_as_inappropriate', 'flag_for_review', 'approve_posting', 'remove_posting']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_title', 'department', 'location', 'classification')
        }),
        ('Requirements', {
            'fields': ('alternation_criteria', 'language_profile')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'creator')
        }),
        ('Dates', {
            'fields': ('posting_date', 'expiration_date', 'created_at', 'updated_at')
        }),
        ('Moderation', {
            'fields': ('moderation_status', 'moderation_notes', 'moderation_date', 'moderation_by'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        """Override to show all job postings, including expired or flagged entries."""
        qs = super().get_queryset(request)
        return qs
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = "Active"
    
    def creator_display(self, obj):
        if obj.creator:
            return f"{obj.creator.first_name} {obj.creator.last_name}"
        return "Unknown"
    creator_display.short_description = "Creator"
    
    def save_model(self, request, obj, form, change):
        """Override to log moderation changes."""
        if change and 'moderation_status' in form.changed_data:
            obj.moderation_date = timezone.now()
            obj.moderation_by = request.user.username
            
            # Log the action
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(obj).pk,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message=f"Changed moderation status to {obj.get_moderation_status_display()}"
            )
            
            messages.success(request, f"Moderation status updated to {obj.get_moderation_status_display()}")
        
        super().save_model(request, obj, form, change)
    
    def mark_as_inappropriate(self, request, queryset):
        """Mark selected job postings as inappropriate."""
        updated = queryset.update(
            moderation_status='INAPPROPRIATE',
            moderation_date=timezone.now(),
            moderation_by=request.user.username
        )
        
        # Log the action for each object
        for obj in queryset:
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(obj).pk,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message="Marked as inappropriate via admin action"
            )
        
        self.message_user(request, f"{updated} job postings marked as inappropriate.")
    mark_as_inappropriate.short_description = "Mark selected postings as inappropriate"
    
    def flag_for_review(self, request, queryset):
        """Flag selected job postings for review."""
        updated = queryset.update(
            moderation_status='FLAGGED',
            moderation_date=timezone.now(),
            moderation_by=request.user.username
        )
        
        # Log the action for each object
        for obj in queryset:
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(obj).pk,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message="Flagged for review via admin action"
            )
        
        self.message_user(request, f"{updated} job postings flagged for review.")
    flag_for_review.short_description = "Flag selected postings for review"
    
    def approve_posting(self, request, queryset):
        """Approve selected job postings."""
        updated = queryset.update(
            moderation_status='APPROVED',
            moderation_date=timezone.now(),
            moderation_by=request.user.username
        )
        
        # Log the action for each object
        for obj in queryset:
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(obj).pk,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message="Approved via admin action"
            )
        
        self.message_user(request, f"{updated} job postings approved.")
    approve_posting.short_description = "Approve selected postings"
    
    def remove_posting(self, request, queryset):
        """Remove selected job postings (mark as removed, don't delete)."""
        updated = queryset.update(
            moderation_status='REMOVED',
            moderation_date=timezone.now(),
            moderation_by=request.user.username
        )
        
        # Log the action for each object
        for obj in queryset:
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(obj).pk,
                object_id=obj.pk,
                object_repr=str(obj),
                action_flag=CHANGE,
                change_message="Removed via admin action"
            )
        
        self.message_user(request, f"{updated} job postings removed.")
    remove_posting.short_description = "Remove selected postings"
