from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from .models import School, Project
from django.db.models import Sum

def projects_by_school(request, school_id: int):
    school = get_object_or_404(School, pk=school_id)
    qs = school.projects.order_by('-start_date')
    return render(request, 'projects/list.html', {'school': school, 'projects': qs})

def project_detail(request, pk: int):
    p = get_object_or_404(Project, pk=pk)
    return render(request, 'projects/detail.html', {'p': p})


def dashboard(request):
    schools = School.objects.all().order_by('name')
    latest = Project.objects.select_related('school').order_by('-start_date')[:5]
    totals = Project.objects.aggregate(budget=Sum('budget'), spent=Sum('spent'))
    return render(request, "dashboard.html", {
        "schools": schools,
        "latest": latest,
        "totals": totals,
    })
