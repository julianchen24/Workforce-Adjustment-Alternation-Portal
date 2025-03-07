from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import ListView
from .models import WaapUser

def index(request):
    """Home page view for the WAAP application."""
    return HttpResponse("<h1>Welcome to the Workforce Adjustment Alternation Portal (WAAP)</h1>")

class UserListView(ListView):
    """View to display all users in the system."""
    model = WaapUser
    template_name = 'waap/user_list.html'
    context_object_name = 'users'
