# projects/admin.py
from django.contrib import admin
from .models import School, Project, Expense, SpendingLimit, Event
from .models import Delegation

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
    list_display = (
        "title",
        "from_user",
        "to_user",
        "school",
        "project",
        "start_date",
        "end_date",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "school", "project")
    search_fields = ("title", "from_user__username", "to_user__username", "to_user__email")

from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "school", "status", "uploaded_by", "created_at")
    list_filter = ("status", "school", "project")
    search_fields = ("title", "description")
    readonly_fields = ("uploaded_by", "created_at")

    def save_model(self, request, obj, form, change):
        # se è nuovo, salvo chi l'ha caricato
        if not obj.pk and not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
