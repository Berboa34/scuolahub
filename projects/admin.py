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


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("project", "date", "vendor", "category", "amount", "document_no", "created_by")
    list_filter = ("project", "category", "date")
    search_fields = ("vendor", "document_no")


@admin.register(SpendingLimit)
class SpendingLimitAdmin(admin.ModelAdmin):
    list_display = ("project", "category", "percent", "basis")
    list_filter = ("basis", "category", "project")
