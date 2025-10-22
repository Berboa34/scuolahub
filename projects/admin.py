from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import School, Project

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "codice_meccanografico")
    search_fields = ("name", "codice_meccanografico")

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "program", "status", "budget", "spent")
    list_filter = ("program", "status", "school")
    search_fields = ("title", "cup", "cig")
