from django.contrib import admin
from .models import WaapUser, Department, JobPosting

@admin.register(WaapUser)
class WaapUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'department', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'department')
    list_filter = ('department', 'created_at')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'department', 'location', 'classification', 
                   'language_profile', 'posting_date', 'expiration_date', 'is_active')
    list_filter = ('department', 'classification', 'language_profile', 'posting_date')
    search_fields = ('job_title', 'location')
    readonly_fields = ('posting_date', 'created_at', 'updated_at')
    fieldsets = (
        ('Job Information', {
            'fields': ('job_title', 'department', 'location', 'classification')
        }),
        ('Requirements', {
            'fields': ('alternation_criteria', 'language_profile')
        }),
        ('Contact Information', {
            'fields': ('contact_email',)
        }),
        ('Dates', {
            'fields': ('posting_date', 'expiration_date', 'created_at', 'updated_at')
        }),
    )
    
    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = "Active"
