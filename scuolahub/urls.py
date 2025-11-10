from django.contrib import admin
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from django.http import HttpResponse
def ping(request): return HttpResponse("pong")

# importa tutte le view dal tuo app "projects"
from projects import views as pviews

urlpatterns = [
    path('admin/', admin.site.urls),

    # HOME
    path('', pviews.dashboard, name='dashboard'),

    # Progetti
    path('scuole/<int:school_id>/progetti/', pviews.projects_by_school, name='projects_by_school'),
    path('progetti/<int:pk>/', pviews.project_detail, name='project_detail'),

    # Auth
    path('accounts/login/',
         auth_views.LoginView.as_view(template_name='registration/login.html'),
         name='login'),

    path('accounts/logout/',
         auth_views.LogoutView.as_view(next_page=reverse_lazy('login')),
         name='logout'),

    # --- DEBUG DB ---
    path('debug/db/', pviews.db_check, name='db_check'),
    path('ping/', ping, name='ping'),

]

from django.http import HttpResponse
def ping(request): return HttpResponse("pong")
