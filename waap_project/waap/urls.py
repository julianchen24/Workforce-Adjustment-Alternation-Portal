from django.urls import path
from . import views

app_name = 'waap'

urlpatterns = [
    path('', views.index, name='index'),
    path('users/', views.UserListView.as_view(), name='user_list'),
]
