# projects/migrations/0005_alter_expense_options_alter_spendinglimit_options_and_more.py
from django.db import migrations, models
from django.utils import timezone
from decimal import Decimal

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_alter_expense_options_remove_expense_doc_no_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='expense',
            options={'ordering': ['-date', '-id']},
        ),
        migrations.AlterModelOptions(
            name='spendinglimit',
            options={'verbose_name': 'Limite di spesa', 'verbose_name_plural': 'Limiti di spesa'},
        ),
        # --- Expense cleanup ---
        migrations.RemoveField(
            model_name='expense',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='expense',
            name='document_no',
        ),
        migrations.AddField(
            model_name='expense',
            name='document',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='expense',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='expense',
            name='category',
            field=models.CharField(choices=[('MATERIALS', 'Materiali'), ('SERVICES', 'Servizi'), ('TRAINING', 'Formazione'), ('OTHER', 'Altro')], default='OTHER', max_length=32),
        ),
        migrations.AlterField(
            model_name='expense',
            name='date',
            field=models.DateField(default=timezone.now),
        ),
        migrations.AlterField(
            model_name='expense',
            name='note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='expense',
            name='vendor',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),

        # --- Project tweaks ---
        migrations.AlterField(
            model_name='project',
            name='budget',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='project',
            name='cig',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='cup',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='project',
            name='program',
            field=models.CharField(choices=[('PNRR', 'PNRR'), ('FESR', 'FESR'), ('FSE', 'FSE'), ('ERASMUS', 'Erasmus+'), ('ALTRO', 'Altro')], default='PNRR', max_length=16),
        ),
        migrations.AlterField(
            model_name='project',
            name='spent',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12),
        ),
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Bozza'), ('ACTIVE', 'In corso'), ('CLOSED', 'Chiuso')], default='ACTIVE', max_length=16),
        ),

        # --- School tweak ---
        migrations.AlterField(
            model_name='school',
            name='code',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),

        # --- SpendingLimit: nuovi campi ---
        migrations.AddField(
            model_name='spendinglimit',
            name='base',
            field=models.CharField(
                choices=[('BUDGET', 'Budget'), ('SPENT', 'Speso attuale'), ('REMAINING', 'Residuo')],
                default='BUDGET',
                help_text='Valore di riferimento per il calcolo: Budget, Speso o Residuo.',
                max_length=16
            ),
        ),
        migrations.AddField(
            model_name='spendinglimit',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='spendinglimit',
            name='percentage',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=6),
        ),
        migrations.AlterField(
            model_name='spendinglimit',
            name='category',
            field=models.CharField(choices=[('MATERIALS', 'Materiali'), ('SERVICES', 'Servizi'), ('TRAINING', 'Formazione'), ('OTHER', 'Altro')], max_length=32),
        ),
        # Rimuoviamo i vecchi nomi errati *dopo* aver aggiunto i nuovi
        migrations.RemoveField(
            model_name='spendinglimit',
            name='basis',
        ),
        migrations.RemoveField(
            model_name='spendinglimit',
            name='percent',
        ),

        # --- SOLO ORA: unique_together che usa 'base' ---
        migrations.AlterUniqueTogether(
            name='spendinglimit',
            unique_together={('project', 'category', 'base')},
        ),
    ]
