# projects/admin.py
from django.contrib import admin
from .models import School, Project, Expense, SpendingLimit, Event


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