from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy   # <— aggiungi reverse_lazy


from projects.views import dashboard  # <— importiamo SOLO ciò che esiste



from projects.views import dashboard, project_detail, projects_by_school, db_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('scuole/<int:school_id>/progetti/', projects_by_school, name='projects_by_school'),
    path('progetti/<int:pk>/', project_detail, name='project_detail'),

    # --- Debug DB ---
    path('debug/db/', db_check, name='db_check'),
]
