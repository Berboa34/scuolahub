from django.contrib import admin
from .models import School, Project, Expense, SpendingLimit


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "program", "status", "budget", "spent", "school")
    list_filter = ("program", "status", "school")
    search_fields = ("title", "cup", "cig")
    ordering = ("title",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("project", "date", "category", "vendor", "amount", "note")
    list_filter = ("category", "project")
    search_fields = ("vendor", "note")
    ordering = ("-date",)


@admin.register(SpendingLimit)
class SpendingLimitAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "base", "percentage", "created_at")
    list_filter = ("category", "base", "project")
    search_fields = ("project__title",)
    ordering = ("project", "category")
