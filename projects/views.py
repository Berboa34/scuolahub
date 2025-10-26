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
