from django import forms
from .models import Expense, SpendingLimit


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["date", "vendor", "category", "amount", "document_no", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }


class SpendingLimitForm(forms.ModelForm):
    class Meta:
        model = SpendingLimit
        fields = ["category", "percent", "basis"]
        widgets = {
            "percent": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }
