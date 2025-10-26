# projects/apps.py
from django.apps import AppConfig

class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'

    def ready(self):
        # collega i signals SOLO quando le app sono pronte
        try:
            from . import signals  # noqa: F401
        except Exception:
            # se non usi i signals puoi anche lasciare pass
            pass
