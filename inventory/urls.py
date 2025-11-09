from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

# app_name = 'inventory'  # optional but useful if you ever include this app with a namespace

urlpatterns = [
    path('', views.medicine_list, name='medicine_list'),
    path('add/', views.medicine_add, name='medicine_add'),
    path('edit/<int:pk>/', views.medicine_edit, name='medicine_edit'),
    path('delete/<int:pk>/', views.medicine_delete, name='medicine_delete'),
    path('api/medicines/', views.api_medicines, name='api_medicines'),
    path('ai_query/', views.ai_query, name="ai_query"),
    path('login/', auth_views.LoginView.as_view(template_name='inventory/login.html'), name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('test-gemini/', views.test_gemini, name='test_gemini'),
    path("list-models/", views.list_models, name="list_models"),
    path('dashboard/', views.dashboard, name='dashboard'),
]


    # path('login/', auth_views.LoginView.as_view(template_name='inventory/login.html'), name='login'),
