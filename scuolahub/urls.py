from django.contrib import admin
from django.urls import path, reverse_lazy, include
from django.contrib.auth import views as auth_views

from projects import views as pviews
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home protetta (Dashboard)
    path('', pviews.dashboard, name='dashboard'),

    # Progetti
    path('progetti/', pviews.projects_list, name='projects_list'),
    path('progetti/<int:pk>/', pviews.project_detail, name='project_detail'),
    path('scuole/<int:school_id>/progetti/', pviews.projects_by_school, name='projects_by_school'),

    # Sezioni (per ora placeholder)
    path('calendario/view/', pviews.calendar_view, name='calendar_view'),
    path('calendario/', pviews.calendar_view, name='calendar'),
# Eliminazione evento calendario
    path('eventi/<int:pk>/elimina/', pviews.event_delete, name='event_delete'),

    path('documenti/', TemplateView.as_view(template_name='documents.html'), name='documents'),
    path('impostazioni/', TemplateView.as_view(template_name='settings.html'), name='settings'),

    # Auth (login/logout)
    path('accounts/login/',  auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),

    # Delete/Update risorse
    path('spese/<int:pk>/elimina/', pviews.expense_delete, name='expense_delete'),
    path('limiti/<int:pk>/elimina/', pviews.limit_delete, name='limit_delete'),
    path('limiti/<int:pk>/modifica/', pviews.limit_update, name='limit_update'),


    path("deleghe/", pviews.deleghe_view, name="deleghe"),
    path("deleghe/<int:pk>/elimina/", pviews.delegation_delete, name="delegation_delete"),

    # DOCUMENTI
    path('documenti/', pviews.documents_view, name='documents'),
    path('documenti/<int:pk>/elimina/', pviews.document_delete, name='document_delete'),

    path("mie-deleghe/", pviews.my_delegations_view, name="my_delegations"),
    path('deleghe/<int:pk>/conferma/', pviews.delegation_confirm, name='delegation_confirm'),

    # Bandi / Call
    path('bandi/', pviews.bandi_list, name='bandi_list'),

    path('bandi/<int:pk>/', pviews.bando_detail, name='bando_detail'),

    path('notifiche/<int:pk>/', pviews.notification_read, name='notification_read'),





]
