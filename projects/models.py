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


from django.conf import settings

class Delegation(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "In attesa di conferma"),  # Nuovo stato
        ("ACTIVE", "Attiva"),
        ("CONFIRMED", "Confermata"),
        # Nuovo stato (usata se Active significa "non revocata" e Confirmed significa "accettata")
        ("REVOKED", "Revocata"),
        ("REJECTED", "Rifiutata"),  # (Opzionale)
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="delegations",
        null=True,  # <--- AGGIUNGI O RIPRISTINA QUESTO
        blank=True,  # <--- AGGIUNGI O RIPRISTINA QUESTO
    )
    collaborator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # va bene, se elimini l'utente si eliminano anche le deleghe
        related_name="delegations",
        null=True,
        blank=True,
    )
    role_label = models.CharField("Ruolo delegato", max_length=100, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.collaborator} → {self.project} ({self.get_status_display()})"

class CallForProposal(models.Model):
    """
    Bando unificato: rappresenta bandi PNRR, FESR, FSE, Erasmus+, ecc.
    indipendentemente dalla fonte originale.
    """
    PROGRAM_CHOICES = Project.PROGRAM_CHOICES
    STATUS_CHOICES = [
        ("DRAFT", "Bozza interna"),
        ("OPEN", "Aperto"),
        ("IN_PREP", "In preparazione progetto"),
        ("CLOSED", "Scaduto"),
        ("FUNDED", "Finanziato"),
        ("NOT_FUNDED", "Non finanziato"),
    ]
    IMPORT_CHOICES = [
        ("MANUAL", "Inserimento manuale"),
        ("CSV", "Import da file"),
        ("EMAIL", "Da email / newsletter"),
        ("API", "Sincronizzato da API esterna"),
    ]

    # Facoltativo: se il bando è specifico per una scuola
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    title = models.CharField("Titolo bando", max_length=255)
    program = models.CharField(
        "Programma",
        max_length=16,
        choices=PROGRAM_CHOICES,
        default="PNRR",
    )
    internal_code = models.CharField(
        "Codice interno / riferimento",
        max_length=50,
        blank=True,
        null=True,
    )

    source_name = models.CharField(
        "Fonte",
        max_length=100,
        help_text="Es. MIM, Regione, Agenzia Erasmus+, Fondazione..."
    )
    source_url = models.URLField(
        "Link al bando ufficiale",
        blank=True,
        null=True,
    )

    publication_date = models.DateField("Data pubblicazione", blank=True, null=True)
    deadline_date = models.DateField("Scadenza", blank=True, null=True)

    status = models.CharField(
        "Stato",
        max_length=12,
        choices=STATUS_CHOICES,
        default="OPEN",
    )

    amount_available = models.DecimalField(
        "Importo disponibile (se noto)",
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
    )

    summary = models.TextField("Sintesi", blank=True, null=True)
    requirements = models.TextField("Requisiti principali", blank=True, null=True)
    notes = models.TextField("Note interne", blank=True, null=True)

    import_source = models.CharField(
        "Origine dati",
        max_length=10,
        choices=IMPORT_CHOICES,
        default="MANUAL",
    )
    imported_at = models.DateTimeField("Inserito il", auto_now_add=True)
    last_update = models.DateTimeField("Ultimo aggiornamento", auto_now=True)

    class Meta:
        ordering = ["-deadline_date", "title"]
        verbose_name = "Bando"
        verbose_name_plural = "Bandi"

    def __str__(self):
        return self.title
