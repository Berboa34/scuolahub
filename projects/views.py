from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Project, School

@login_required
def dashboard(request):
    # mostra solo i progetti / dati della scuola dell'utente
    profile = getattr(request.user, "profile", None)
    if profile and profile.school:
        school = profile.school
        schools = [school]
        latest = Project.objects.filter(school=school).order_by('-start_date')[:6]
        totals = Project.objects.filter(school=school).aggregate(budget=Sum('budget'), spent=Sum('spent'))
    else:
        # fallback: nessuna school assegnata → nessun dato sensibile
        schools = []
        latest = Project.objects.none()
        totals = {"budget": 0, "spent": 0}
    return render(request, "dashboard.html", {
        "schools": schools,
        "latest": latest,
        "totals": totals,
    })
