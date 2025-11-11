from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, F, FloatField, Value, Case, When, Q
from django.http import HttpResponse, Http404

from .models import Project, School, Expense
from .forms import ExpenseForm, SpendingLimitForm


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
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    qs = Project.objects.all()
    if school:
        qs = qs.filter(school=school)

    # Querystring
    q = request.GET.get('q', '').strip()
    program = request.GET.get('program', '').strip()
    status = request.GET.get('status', '').strip()

    # Scelte (preferibilmente da field.choices)
    pf = Project._meta.get_field('program')
    program_choices = list(getattr(pf, "choices", [])) or [(v, v) for v in Project.objects.values_list('program', flat=True).distinct() if v]

    sf = Project._meta.get_field('status')
    status_choices = list(getattr(sf, "choices", [])) or [(v, v) for v in Project.objects.values_list('status', flat=True).distinct() if v]

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(cup__icontains=q) |
            Q(cig__icontains=q) |
            Q(program__icontains=q)
        )
    if program:
        qs = qs.filter(program=program)
    if status:
        qs = qs.filter(status=status)

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

    return render(request, "projects/list.html", {
        "projects": projects,
        "totals": totals,
        "school": school,
        "q": q, "program": program, "status": status,
        "program_choices": program_choices,
        "status_choices": status_choices,
    })


@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(Project, pk=pk)
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Progetto non trovato")

    # ---- FILTRI spese ----
    cat = request.GET.get('cat', '').strip()
    vendor = request.GET.get('vendor', '').strip()

    expenses_qs = Expense.objects.filter(project=project)
    if cat:
        expenses_qs = expenses_qs.filter(category=cat)
    if vendor:
        expenses_qs = expenses_qs.filter(vendor__icontains=vendor)

    expenses = expenses_qs.order_by('-date', '-id')
    totals = expenses_qs.aggregate(total=Sum('amount'))
    total_expenses = totals['total'] or 0

    # percentuale spesa su budget
    percent = 0
    if project.budget and project.budget > 0:
        percent = round((project.spent or 0) * 100 / project.budget, 2)

    # ---- FORM NUOVA SPESA ----
    if request.method == "POST" and request.POST.get("action") == "add_expense":
        form = ExpenseForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.project = project
            exp.created_by = request.user
            exp.save()
            # allinea spent del progetto
            project.spent = Expense.objects.filter(project=project).aggregate(s=Sum('amount'))['s'] or 0
            project.save(update_fields=['spent'])
            return redirect(f"{request.path}?cat={cat}&vendor={vendor}")
    else:
        form = ExpenseForm()

    # ---- LIMITE DI SPESA (calcoli) ----
    limits = project.limits.all()
    basis_amount = {
        'SPENT': Expense.objects.filter(project=project).aggregate(s=Sum('amount'))['s'] or 0,
        'BUDGET': project.budget or 0,
    }
    limits_view = []
    for lim in limits:
        base = basis_amount.get(lim.basis, 0)
        cap_amount = round((float(lim.percent or 0)) * base / 100.0, 2)
        cat_spent = Expense.objects.filter(project=project, category=lim.category)\
                                   .aggregate(s=Sum('amount'))['s'] or 0
        remaining = round(cap_amount - float(cat_spent), 2)
        limits_view.append({
            "obj": lim,
            "cap": cap_amount,
            "spent": round(float(cat_spent), 2),
            "remaining": remaining,
            "over": remaining < 0,
            "base_label": "totale speso" if lim.basis == "SPENT" else "budget",
        })

    # form per nuovo limite
    if request.method == "POST" and request.POST.get("action") == "add_limit":
        lform = SpendingLimitForm(request.POST)
        if lform.is_valid():
            lim = lform.save(commit=False)
            lim.project = project
            lim.save()
            return redirect(request.path)
    else:
        lform = SpendingLimitForm()

    return render(request, "projects/detail.html", {
        "project": project,
        "expenses": expenses,
        "total_expenses": total_expenses,
        "form": form,
        "percent": percent,
        "school": school,
        "cat": cat,
        "vendor": vendor,
        "limits": limits_view,
        "limit_form": lform,
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

    return render(request, "projects/projects_by_school.html",
                  {"school": school, "projects": projects, "totals": totals})


@login_required
def db_check(request):
    qs = Project.objects.select_related("school").order_by("-start_date")
    rows = [f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}" for p in qs[:20]]
    html = "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    return HttpResponse(html)
