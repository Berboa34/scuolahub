from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum
from .models import Project, School

@login_required
def dashboard(request):
    totals = Project.objects.aggregate(budget=Sum('budget'), spent=Sum('spent'))
    latest = Project.objects.order_by('-start_date')[:6]
    schools = School.objects.all()[:1]
    return render(request, "dashboard.html", {
        "totals": totals, "latest": latest, "schools": schools
    })
