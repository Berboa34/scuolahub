from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


# --- Scelte comuni ------------------------------------------------------------

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

CATEGORY_CHOICES = [
    ("MATERIALS", "Materiali"),
    ("SERVICES", "Servizi"),
    ("TRAINING", "Formazione"),
    ("OTHER", "Altro"),
]

LIMIT_BASE_CHOICES = [
    ("BUDGET", "Budget"),
    ("SPENT", "Speso attuale"),
    ("REMAINING", "Residuo"),
]


# --- Modelli ------------------------------------------------------------------

class School(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    program = models.CharField(max_length=16, choices=PROGRAM_CHOICES, default="PNRR")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="ACTIVE")

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Decimal per coerenza con le spese
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    cup = models.CharField(max_length=32, blank=True, null=True)
    cig = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.title

    @property
    def remaining(self) -> Decimal:
        return (self.budget or Decimal("0")) - (self.spent or Decimal("0"))

    @property
    def percent_spent(self) -> float:
        b = float(self.budget or 0)
        s = float(self.spent or 0)
        return (s * 100.0 / b) if b > 0 else 0.0


class Expense(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="expenses")
    date = models.DateField(default=timezone.now)
    vendor = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="OTHER")

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    document = models.CharField(max_length=255, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.project_id} • {self.vendor or '-'} • {self.amount}"


class SpendingLimit(models.Model):
    # stessa logica delle categorie usate su Expense
    CAT_MATERIALI = "MATERIALI"
    CAT_FORMAZIONE = "FORMAZIONE"
    CAT_SERVIZI = "SERVIZI"
    CATEGORY_CHOICES = [
        (CAT_MATERIALI, "Materiali"),
        (CAT_FORMAZIONE, "Formazione"),
        (CAT_SERVIZI, "Servizi"),
    ]

    BASE_BUDGET = "BUDGET"   # percentuale calcolata sul budget allocato
    BASE_SPENT  = "SPENT"    # percentuale calcolata sulla spesa attuale
    BASE_CHOICES = [
        (BASE_BUDGET, "Budget allocato"),
        (BASE_SPENT, "Spesa attuale"),
    ]

    project   = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="limits")
    category  = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    base      = models.CharField(max_length=12, choices=BASE_CHOICES, default=BASE_BUDGET)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "category", "base")

    def __str__(self):
        return f"{self.project} • {self.category} • {self.base} • {self.percentage}%"
