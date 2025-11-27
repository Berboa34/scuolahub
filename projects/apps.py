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


# projects/apps.py
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'

    def ready(self):
        # Collega i segnali (già presente)
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass

        # AGGIUNGI QUESTO: Forza il caricamento del codice Admin
        # Questo assicura che il DelegationAdmin e i suoi metodi custom
        # (come admin_status_display) vengano registrati DOPO che il modello è pronto.
        try:
            from . import admin  # noqa: F401
        except Exception:
            pass