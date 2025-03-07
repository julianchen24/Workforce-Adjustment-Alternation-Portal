from django.contrib import admin
from .models import WaapUser

@admin.register(WaapUser)
class WaapUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'department', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'department')
    list_filter = ('department', 'created_at')
