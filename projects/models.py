from django.db import models
from django.utils import timezone
from decimal import Decimal

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
