from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, F, FloatField, Value, Case, When
from .models import Project, School

@login_required
def dashboard(request):
    # opzionale: filtra per scuola dal profilo
    school = getattr(getattr(request.user, 'profile', None), 'school', None)

    base_qs = Project.objects.all()
    if school:
        base_qs = base_qs.filter(school=school)

    totals = base_qs.aggregate(budget=Sum('budget'), spent=Sum('spent'))
    totals['budget'] = totals['budget'] or 0
    totals['spent']  = totals['spent'] or 0

    latest = base_qs.order_by('-start_date')[:6]
    projects = base_qs.annotate(
        percent_spent=Case(
            When(budget__gt=0, then=(100.0 * F('spent') / F('budget'))),
            default=Value(0.0),
            output_field=FloatField()
        )
    ).order_by('title', 'id')

    return render(request, "dashboard.html", {
        "school": school,
        "totals": totals,
        "latest": latest,
        "projects": projects,
    })

def db_check(request):
    qs = Project.objects.select_related('school').order_by('-start_date')
    rows = [f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}" for p in qs[:20]]
    return HttpResponse(
        "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    )


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
