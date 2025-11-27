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
        ("PENDING", "In attesa di conferma"),
        ("CONFIRMED", "Confermata"),
        ("REJECTED", "Rifiutata"),
        ("REVOKED", "Revocata"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="delegations",
        null=True,
        blank=True,
    )

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations_created",
        verbose_name="Delegante",
        default=1,  # <--- TEMPORANEO! Sostituisci 1 con l'ID di un Admin esistente.
    )

    collaborator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delegations",
        null=True,
        blank=True,
    )
    role_label = models.CharField(
        "Ruolo delegato",
        max_length=100,
        blank=True,
        null=True  # <--- AGGIUNGI null=True
    )
    note = models.TextField(
        blank=True,
        null=True  # <--- AGGIUNGI null=True
    )

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # QUESTO È IL CONTROLLO CRITICO:
        # Se l'oggetto è NUOVO (pk è None)
        if self.pk is None:
            # Imposta lo stato su PENDING, indipendentemente da cosa ha cercato di fare
            # un segnale o un save() precedente. Questo sovrascrive tutto.
            self.status = 'PENDING'

        # Poi esegue il salvataggio standard nel database
        super().save(*args, **kwargs)

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

class Call(models.Model):
    PROGRAM_CHOICES = [
        ("PNRR", "PNRR"),
        ("FESR", "FESR"),
        ("FSE", "FSE"),
        ("ERASMUS", "Erasmus+"),
        ("ALTRO", "Altro"),
    ]

    STATUS_CHOICES = [
        ("APERTO", "Aperto"),
        ("SCADUTO", "Scaduto"),
        ("IN_PROGRAMMAZIONE", "In programmazione"),
    ]

    title = models.CharField(max_length=255)
    program = models.CharField(max_length=20, choices=PROGRAM_CHOICES)
    source = models.CharField(max_length=255, help_text="Ministero, Regione, Fondazione, UE…")
    deadline = models.DateField(blank=True, null=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="APERTO")
    tags = models.CharField(max_length=255, blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-deadline", "title"]

    def __str__(self):
        return self.title


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField()

    # 🔗 delega collegata (può essere vuota per altri tipi di notifica)
    delegation = models.ForeignKey(
        "Delegation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        txt = self.message
        if len(txt) > 50:
            txt = txt[:47] + "..."
        return f"{self.user} – {txt}"



class Milestone(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "In attesa"),
        ("COMPLETED", "Completata"),
        ("DELAYED", "In ritardo"),
        ("CANCELED", "Annullata"),
    ]

    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="milestones",
        verbose_name="Progetto"
    )
    title = models.CharField(max_length=200, verbose_name="Titolo Milestone")
    description = models.TextField(blank=True, null=True, verbose_name="Descrizione")
    due_date = models.DateField(verbose_name="Data di Scadenza")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
        verbose_name="Stato"
    )
    completed_date = models.DateField(blank=True, null=True, verbose_name="Data di Completamento")

    class Meta:
        ordering = ["due_date"]
        verbose_name = "Milestone"
        verbose_name_plural = "Milestone"

    def __str__(self):
        return f"{self.project.title} - {self.title}"