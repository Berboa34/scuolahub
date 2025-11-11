from django.contrib.auth.models import User
from django.db import models

class School(models.Model):
    name = models.CharField(max_length=255)
    codice_meccanografico = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.codice_meccanografico})"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    school = models.ForeignKey(School, null=True, blank=True, on_delete=models.SET_NULL)
    role = models.CharField(max_length=40, default="staff")  # es. dirigente, DSGA, referente

    def __str__(self):
        return f"{self.user.username} ({self.school})"

class Project(models.Model):
    PROGRAM_CHOICES = [("PNRR","PNRR"), ("FESR","FESR"), ("FSE","FSE"), ("ERASMUS","Erasmus+"), ("ALTRO","Altro")]
    STATUS_CHOICES = [("DRAFT","Bozza"), ("ACTIVE","In corso"), ("CLOSED","Chiuso")]

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="projects")
    title = models.CharField(max_length=255)
    program = models.CharField(max_length=10, choices=PROGRAM_CHOICES)
    cup = models.CharField(max_length=30, blank=True)
    cig = models.CharField(max_length=30, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def percent_spent(self):
        return 0 if not self.budget else round((self.spent / self.budget) * 100, 1)

    def __str__(self):
        return self.title

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('ATTREZZATURE', 'Attrezzature'),
        ('SERVIZI', 'Servizi'),
        ('FORMAZIONE', 'Formazione'),
        ('ALTRO', 'Altro'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField()
    vendor = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='ALTRO')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    doc_no = models.CharField("Documento (n°/ID)", max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.project} - {self.vendor} - {self.amount}€"