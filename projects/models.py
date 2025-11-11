from django.db import models
from django.conf import settings


class School(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)  # codice meccanografico, opzionale

    def __str__(self):
        return self.name


PROGRAM_CHOICES = [
    ("PNRR", "PNRR"),
    ("FESR", "FESR"),
    ("FSE", "FSE"),
    ("ERASMUS", "Erasmus+"),
]

STATUS_CHOICES = [
    ("DRAFT", "Bozza"),
    ("ACTIVE", "In corso"),
    ("CLOSED", "Chiuso"),
]


class Project(models.Model):
    title = models.CharField(max_length=255)
    program = models.CharField(max_length=20, choices=PROGRAM_CHOICES, default="PNRR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL)

    cup = models.CharField(max_length=50, blank=True)
    cig = models.CharField(max_length=50, blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return self.title


# Categorie standard per le spese
CATEGORY_CHOICES = [
    ('MATERIALI', 'Materiali'),
    ('SERVIZI', 'Servizi'),
    ('FORMAZIONE', 'Formazione'),
    ('ALTRO', 'Altro'),
]


class Expense(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField()
    vendor = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    document_no = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.project} – {self.vendor or '—'} – {self.amount}"


BASIS_CHOICES = [
    ('BUDGET', 'Percento del budget'),
    ('SPENT',  'Percento del totale speso'),
]


class SpendingLimit(models.Model):
    """
    Regola di limite di spesa per Progetto:
    - category: categoria a cui si applica il limite
    - percent: percentuale (es. 20 = 20%)
    - basis: base di calcolo (BUDGET oppure SPENT)
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='limits')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    percent = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentuale (es. 20 = 20%)")
    basis = models.CharField(max_length=10, choices=BASIS_CHOICES, default='SPENT')

    class Meta:
        unique_together = ('project', 'category', 'basis')

    def __str__(self):
        return f"{self.project} – {self.category} ≤ {self.percent}% di {self.basis}"
