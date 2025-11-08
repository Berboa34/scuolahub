from django.contrib import admin
from django.urls import path

# importa tutte le view dal tuo app "projects"
from projects import views as pviews

urlpatterns = [
    path('admin/', admin.site.urls),

    # HOME
    path('', pviews.dashboard, name='dashboard'),

    # Progetti
    path('scuole/<int:school_id>/progetti/', pviews.projects_by_school, name='projects_by_school'),
    path('progetti/<int:pk>/', pviews.project_detail, name='project_detail'),

    # --- DEBUG DB ---
    path('debug/db/', pviews.db_check, name='db_check'),
]
