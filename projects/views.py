from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
from .models import Project, School

@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    if school:
        projects_qs = Project.objects.filter(school=school)
        schools = [school]
    else:
        # Nessuna scuola associata → niente dati sensibili
        projects_qs = Project.objects.none()
        schools = []

    totals = projects_qs.aggregate(budget=Sum('budget'), spent=Sum('spent'))
    latest = projects_qs.order_by('-start_date')[:6]

    return render(request, "dashboard.html", {
        "schools": schools,
        "latest": latest,
        "totals": totals,
    })

from django.http import HttpResponse

def projects_by_school(request, school_id):
    # Vista minimale giusto per evitare errori e provare il DB
    from .models import Project, School
    name = School.objects.filter(id=school_id).values_list('name', flat=True).first() or "Sconosciuta"
    cnt  = Project.objects.filter(school_id=school_id).count()
    return HttpResponse(f"School {school_id} ({name}) — {cnt} progetti")

def project_detail(request, pk):
    # Se hai già una project_detail reale, lascia la tua.
    from .models import Project
    p = Project.objects.filter(id=pk).first()
    if not p:
        return HttpResponse("Progetto non trovato", status=404)
    return HttpResponse(f"Dettaglio Progetto: {p.title} — Budget €{p.budget}")
