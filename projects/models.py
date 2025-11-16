from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.conf import settings



class School(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    PROGRAM_CHOICES = [
        ("PNRR", "PNRR"),
        ("FESR", "FESR"),
        ("FSE", "FSE"),
        ("ERASMUS", "Erasmus+"),
        ("ALTRO", "Altro"),
    ]
    STATUS_CHOICES = [
        ("DRAFT", "Bozza"),
        ("ACTIVE", "In corso"),
        ("CLOSED", "Chiuso"),
    ]

    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    program = models.CharField(max_length=16, choices=PROGRAM_CHOICES, default="PNRR")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    budget = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    cup = models.CharField(max_length=32, blank=True, null=True)
    cig = models.CharField(max_length=32, blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="ACTIVE")

    def __str__(self):
        return self.title


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ("MATERIALS",  "Materiali"),
        ("SERVICES",   "Servizi"),
        ("TRAINING",   "Formazione"),
        ("OTHER",      "Altro"),
    ]
    project   = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="expenses")
    date      = models.DateField(default=timezone.now)
    vendor    = models.CharField(max_length=255, blank=True, null=True)
    category  = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="OTHER")
    amount    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    document  = models.CharField(max_length=255, blank=True, null=True)
    note      = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.project} - € {self.amount}"


class SpendingLimit(models.Model):
    # Base di calcolo: coerente con le viste
    BASE_CHOICES = [
        ("BUDGET",    "Budget"),
        ("SPENT",     "Speso attuale"),
        ("REMAINING", "Residuo"),
    ]
    CATEGORY_CHOICES = [
        ("MATERIALS",  "Materiali"),
        ("SERVICES",   "Servizi"),
        ("TRAINING",   "Formazione"),
        ("OTHER",      "Altro"),
    ]

    project    = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="limits")
    category   = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    base       = models.CharField(max_length=16, choices=BASE_CHOICES, default="BUDGET")
    percentage = models.DecimalField(max_digits=6, decimal_places=2, help_text="Percentuale, es. 20 = 20%")
    created_at = models.DateTimeField(auto_now_add=True)
    note       = models.CharField(max_length=255, blank=True, null=True)



    class Meta:
        ordering = ["category", "base", "id"]
        unique_together = (("project", "category", "base"),)

    def __str__(self):
        return f"{self.project} – {self.category} {self.percentage}% su {self.base}"

class Event(models.Model):
    """
    Evento di calendario (personale, per ora) legato a:
    - una scuola (opzionale)
    - un progetto (opzionale)
    - un utente (owner) -> calendario personale
    """
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    all_day = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.title} ({self.date})"


from django.conf import settings
# ...
# qui sopra hai già School, Project, Expense, SpendingLimit, Event, ecc.

class Delegation(models.Model):
    """
    Delega assegnata da un utente (from_user) a un collaboratore (to_user),
    eventualmente legata a una scuola e/o a un progetto specifico.
    """
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Scuola a cui si riferisce la delega (facoltativa).",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Progetto specifico collegato alla delega (facoltativo).",
    )

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_given",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_received",
    )

    title = models.CharField(max_length=200, help_text="Oggetto / titolo della delega")
    scope = models.TextField(
        blank=True,
        null=True,
        help_text="Descrizione dell'ambito (es. gestione acquisti PNRR).",
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} → {self.to_user}"


class Document(models.Model):
    """
    Documento condiviso su ScuolaHub.
    - title: nome leggibile del documento
    - file: file caricato
    - project: (opzionale) progetto collegato
    - uploaded_by: utente che lo ha caricato
    - uploaded_at: data/ora di caricamento
    - is_final: se vero, considerato "definitivo" (bloccato)
    """
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="documents/")
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        if self.project:
            return f"{self.title} ({self.project.title})"
        return self.title