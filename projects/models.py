from decimal import Decimal
from django.db import models
from django.utils import timezone


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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="limits")
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)

    # Base del calcolo del limite (NUOVO CAMPO richiesto dalle views)
    base = models.CharField(
        max_length=16,
        choices=LIMIT_BASE_CHOICES,
        default="BUDGET",
        help_text="Valore di riferimento per il calcolo: Budget, Speso o Residuo.",
    )

    # percentuale come Decimal (es. 20.00)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Limite di spesa"
        verbose_name_plural = "Limiti di spesa"
        unique_together = [("project", "category", "base")]

    def __str__(self):
        return f"{self.project_id} · {self.get_category_display()} · {self.get_base_display()} · {self.percentage}%"
