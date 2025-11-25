# projects/admin.py
from django.contrib import admin
from .models import School, Project, Expense, SpendingLimit, Event, Document
from .models import Delegation
from .models import Call, Notification

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "program", "status", "budget", "spent", "start_date", "end_date")
    list_filter = ("program", "status", "school")
    search_fields = ("title", "cup", "cig")
    autocomplete_fields = ("school",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("project", "date", "vendor", "category", "amount", "document")
    list_filter = ("category", "date", "project")
    search_fields = ("vendor", "document", "note")
    autocomplete_fields = ("project",)
    date_hierarchy = "date"
    ordering = ("-date", "-id")


@admin.register(SpendingLimit)
class SpendingLimitAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "base", "percentage", "created_at", "note")
    list_filter = ("project", "category", "base")
    search_fields = ("project__title", "note")
    autocomplete_fields = ("project",)
    ordering = ("project", "category", "base")

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "owner", "school", "project")
    list_filter = ("school", "owner", "date")
    search_fields = ("title", "description")


@admin.register(Delegation)
class DelegationAdmin(admin.ModelAdmin):
    list_display = ("project", "collaborator", "role_label", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("project__title", "collaborator__username", "role_label")
    readonly_fields = ("created_at",)

from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """
    Admin per i Document:
    - niente 'school' o 'status'
    - usiamo 'uploaded_at' (non 'created_at')
    """
    list_display = ("title", "project", "uploaded_by", "uploaded_at", "is_final")
    list_filter = ("project", "uploaded_by", "is_final")
    search_fields = ("title", "project__title", "uploaded_by__username")
    readonly_fields = ("uploaded_at",)


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ("title", "program", "status", "deadline", "budget")
    list_filter = ("program", "status")
    search_fields = ("title", "source", "tags")
    ordering = ("-deadline",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "user")
    search_fields = ("message", "user__username")
    readonly_fields = ("created_at",)