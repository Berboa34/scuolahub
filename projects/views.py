# projects/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.db.models import Sum, F, FloatField, Value, Case, When, Q

from .models import Project, School, Expense   # <-- aggiunto Expense
from .forms import ExpenseForm                 # <-- aggiunto form spese


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    qs = Project.objects.all()
    if school:
        qs = qs.filter(school=school)

    totals = qs.aggregate(budget=Sum("budget"), spent=Sum("spent"))
    totals["budget"] = totals["budget"] or 0
    totals["spent"] = totals["spent"] or 0

    latest = qs.order_by("-start_date")[:6]

    return render(request, "dashboard.html", {
        "school": school,
        "totals": totals,
        "latest": latest,
    })


@login_required
def projects_list(request):
    """Lista progetti con filtri server-side e KPI totali."""
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    qs = Project.objects.all()
    if school:
        qs = qs.filter(school=school)

    # --- filtri ---
    q = request.GET.get('q', '').strip()
    program = request.GET.get('program', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(cup__icontains=q) |
            Q(cig__icontains=q) |
            Q(program__icontains=q)
        )
    if program:
        qs = qs.filter(program__iexact=program)
    if status:
        qs = qs.filter(status__iexact=status)

    projects = qs.annotate(
        percent_spent=Case(
            When(budget__gt=0, then=100.0 * F("spent") / F("budget")),
            default=Value(0.0),
            output_field=FloatField(),
        )
    ).order_by("title", "id")

    totals = qs.aggregate(budget=Sum("budget"), spent=Sum("spent"))
    totals["budget"] = totals["budget"] or 0
    totals["spent"] = totals["spent"] or 0

    # per popolare le tendine
    programs = Project.objects.values_list('program', flat=True).distinct().order_by('program')
    statuses = Project.objects.values_list('status', flat=True).distinct().order_by('status')

    return render(request, "projects/list.html", {
        "projects": projects,
        "totals": totals,
        "school": school,
        "q": q, "program": program, "status": status,
        "programs": [p for p in programs if p],
        "statuses": [s for s in statuses if s],
    })


@login_required
def project_detail(request, pk: int):
    """Dettaglio progetto con elenco spese e form per aggiungerne una."""
    project = get_object_or_404(Project, pk=pk)
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Progetto non trovato")

    expenses = Expense.objects.filter(project=project)
    totals = expenses.aggregate(total=Sum('amount'))
    total_expenses = totals['total'] or 0

    # percentuale spesa su budget
    percent = 0
    if project.budget and project.budget > 0:
        percent = round((project.spent or 0) * 100 / project.budget, 2)

    if request.method == "POST":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.project = project
            exp.created_by = request.user
            exp.save()
            # aggiorna campo 'spent' del progetto in base alle spese
            project.spent = Expense.objects.filter(project=project).aggregate(s=Sum('amount'))['s'] or 0
            project.save(update_fields=['spent'])
            return redirect('project_detail', pk=project.pk)
    else:
        form = ExpenseForm()

    return render(request, "projects/detail.html", {
        "project": project,
        "expenses": expenses,
        "total_expenses": total_expenses,
        "form": form,
        "percent": percent,
        "school": school,
    })


@login_required
def projects_by_school(request, school_id: int):
    school = get_object_or_404(School, pk=school_id)
    qs = Project.objects.filter(school=school)

    totals = qs.aggregate(budget=Sum("budget"), spent=Sum("spent"))
    totals["budget"] = totals["budget"] or 0
    totals["spent"] = totals["spent"] or 0

    projects = qs.annotate(
        percent_spent=Case(
            When(budget__gt=0, then=100.0 * F("spent") / F("budget")),
            default=Value(0.0),
            output_field=FloatField(),
        )
    ).order_by("title", "id")

    return render(request, "projects/projects_by_school.html", {
        "school": school,
        "projects": projects,
        "totals": totals
    })


@login_required
def db_check(request):
    qs = Project.objects.select_related("school").order_by("-start_date")
    rows = [f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}" for p in qs[:20]]
    html = "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    return HttpResponse(html)
