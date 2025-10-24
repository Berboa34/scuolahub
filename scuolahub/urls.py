from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views

from projects.views import dashboard, projects_by_school, project_detail

urlpatterns = [
    path('admin/', admin.site.urls),

    # HOME = dashboard protetta
    path('', dashboard, name='dashboard'),

    # Progetti
    path('scuole/<int:school_id>/progetti/', projects_by_school, name='projects_by_school'),
    path('progetti/<int:pk>/', project_detail, name='project_detail'),

    # Auth (login/logout)
    path('accounts/login/',  auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
