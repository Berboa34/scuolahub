# projects/admin.py
from django.contrib import admin
from .models import School, Project

# --- Admin School
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")

# --- Admin Project
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "status", "budget", "spent", "start_date", "end_date")
    list_filter = ("school", "status")
    search_fields = ("title", "cup", "cig")

# --- Admin Profile (se esiste)
try:
    from .models import Profile

    @admin.register(Profile)
    class ProfileAdmin(admin.ModelAdmin):
        list_display = ("user", "school", "role")
        list_filter = ("school", "role")
        search_fields = ("user__username", "user__email")

except Exception:
    # Nessun Profile nel modello: nessuna registrazione e nessun errore
    pass
