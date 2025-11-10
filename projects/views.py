from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, F, FloatField, Value, Case, When
from .models import Project, School

@login_required
def dashboard(request):
    """
    Dashboard dinamica:
    - Se l'utente ha un profilo con scuola collegata, filtra per quella scuola.
    - Calcola KPI (budget totale, spesa totale).
    - Elenca ultimi progetti e tutti i progetti con percentuale di spesa.
    """
    # Prova a recuperare la scuola dal profilo utente, se esiste
    school = None
    try:
        # se hai un OneToOne Profile con campo 'school'
        school = request.user.profile.school
    except Exception:
        school = None

    base_qs = Project.objects.all()
    if school:
        base_qs = base_qs.filter(school=school)

    # KPI aggregati
    totals = base_qs.aggregate(budget=Sum('budget'), spent=Sum('spent'))
    totals['budget'] = totals['budget'] or 0
    totals['spent'] = totals['spent'] or 0

    # Lista ultimi progetti
    latest = base_qs.order_by('-start_date')[:6]

    # Tutti i progetti con percentuale di spesa calcolata lato DB
    projects = base_qs.annotate(
        percent_spent=Case(
            When(budget__gt=0, then=(100.0 * F('spent') / F('budget'))),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).order_by('title', 'id')

    context = {
        "school": school,
        "totals": totals,
        "latest": latest,
        "projects": projects,
    }
    return render(request, "dashboard.html", context)


# --- Viste minime di appoggio per non rompere gli URL esistenti ---

@login_required
def projects_by_school(request, school_id):
    sch = get_object_or_404(School, pk=school_id)
    cnt = Project.objects.filter(school=sch).count()
    return HttpResponse(f"School {sch.name} — {cnt} progetti")

@login_required
def project_detail(request, pk):
    p = get_object_or_404(Project, pk=pk)
    # Placeholder sintetico per evitare dipendenze da template aggiuntivi
    return HttpResponse(
        f"Dettaglio Progetto: {p.title} — Programma: {getattr(p, 'program', '-')}"
        f" — Budget: €{p.budget} — Speso: €{p.spent}"
    )
