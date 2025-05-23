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
    path('register/', views.user_registration, name='user_registration'),
    path('profile/edit/', views.user_profile_edit, name='user_profile_edit'),
    
    # Job Posting URLs
    path('job-postings/', views.JobPostingListView.as_view(), name='job_posting_list'),
    path('job-postings/create/', views.job_posting_create, name='job_posting_create'),
    path('job-postings/<int:pk>/', views.job_posting_detail, name='job_posting_detail'),
    path('job-postings/<int:pk>/delete-request/', views.job_posting_delete_request, name='job_posting_delete_request'),
    path('job-postings/delete/<str:token>/', views.job_posting_delete_confirm, name='job_posting_delete_confirm'),
    
    # Public Job Posting URLs
    path('browse/', views.PublicJobPostingView.as_view(), name='public_job_postings'),
    
    # Contact Form URLs
    path('job-postings/<int:pk>/contact/', views.contact_form, name='contact_form'),
]
