from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy   # <— aggiungi reverse_lazy


from projects.views import dashboard  # <— importiamo SOLO ciò che esiste

urlpatterns = [
    path('admin/', admin.site.urls),

    # HOME = dashboard protetta
    path('', dashboard, name='dashboard'),

    # Auth (login/logout)
    path('accounts/login/',  auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
