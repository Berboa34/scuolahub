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
from .models import Project, School

def db_check(request):
    qs = Project.objects.select_related('school').order_by('-start_date')
    # Prime 20 righe per prova
    rows = [
        f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}"
        for p in qs[:20]
    ]
    html = "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    return HttpResponse(html)
