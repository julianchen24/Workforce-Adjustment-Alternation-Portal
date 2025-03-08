from django.urls import path
from . import views

app_name = 'waap'

urlpatterns = [
    path('', views.index, name='index'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    
    # Authentication URLs
    path('login/', views.login_request, name='login_request'),
    path('login/verify/<str:token>/', views.login_verify, name='login_verify'),
    path('logout/', views.logout, name='logout'),
    
    # Job Posting URLs
    path('job-postings/create/', views.job_posting_create, name='job_posting_create'),
]
