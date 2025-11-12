from django.db import migrations, models
import django.utils.timezone
from decimal import Decimal

def set_defaults(apps, schema_editor):
    # Se esistono record vecchi senza base/percentage, diamo valori di default
    SpendingLimit = apps.get_model("projects", "SpendingLimit")
    for sl in SpendingLimit.objects.all():
        if not hasattr(sl, "base") or sl.base is None or sl.base == "":
            sl.base = "BUDGET"
        if not hasattr(sl, "percentage") or sl.percentage is None:
            sl.percentage = Decimal("0.00")
        if not hasattr(sl, "created_at") or sl.created_at is None:
            sl.created_at = django.utils.timezone.now()
        sl.save(update_fields=["base", "percentage", "created_at"])

class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0006_alter_spendinglimit_options_alter_spendinglimit_base_and_more"),
        # Se il tuo ultimo file NON è 0005... aggiorna qui il nome per puntare all'ultima migrazione presente nel repo
    ]

    operations = [
        # 1) Aggiungi i campi nuovi se non ci sono già (Render/apply farà il check)
        migrations.AddField(
            model_name="spendinglimit",
            name="base",
            field=models.CharField(
                max_length=10,
                choices=[("BUDGET", "Percentuale del Budget"), ("SPENT", "Percentuale della Spesa attuale")],
                default="BUDGET",
            ),
        ),
        migrations.AddField(
            model_name="spendinglimit",
            name="percentage",
            field=models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00")),
        ),
        migrations.AddField(
            model_name="spendinglimit",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),  # temporaneamente null=True per poter valorizzare
        ),

        # 2) Popola default su righe esistenti
        migrations.RunPython(set_defaults, migrations.RunPython.noop),

        # 3) Rendi NOT NULL created_at dopo averlo popolato
        migrations.AlterField(
            model_name="spendinglimit",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),

        # 4) Rimuovi eventuali vecchi campi storici se esistono nelle vecchie migration (ignora se già rimossi)
        # Se 'basis' e 'percent' NON esistono più nelle tue migration precedenti, puoi commentare queste due righe.
        # migrations.RemoveField(model_name="spendinglimit", name="basis"),
        # migrations.RemoveField(model_name="spendinglimit", name="percent"),

        # 5) Applica il unique_together corretto
        migrations.AlterUniqueTogether(
            name="spendinglimit",
            unique_together={("project", "category", "base")},
        ),
    ]
