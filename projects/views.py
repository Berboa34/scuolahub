from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, FloatField, Value, Case, When
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import Project, School, Expense, SpendingLimit

CATEGORIES = [
    ("MATERIALS", "Materiali"),
    ("SERVICES", "Servizi"),
    ("TRAINING", "Formazione"),
    ("OTHER", "Altro"),
]

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

    # filtri GET
    q = (request.GET.get("q") or "").strip().lower()
    program = (request.GET.get("program") or "").strip().upper()
    status = (request.GET.get("status") or "").strip().upper()

    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(cup__icontains=q) | qs.filter(cig__icontains=q)
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
    })


@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(Project, pk=pk)
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Progetto non trovato")

    # ---- POST handling
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_expense":
            # campi input
            date = request.POST.get("date")
            category = request.POST.get("category")
            vendor = request.POST.get("vendor") or ""
            amount_str = (request.POST.get("amount") or "0").strip().replace(",", ".")
            note = request.POST.get("note") or ""

            # usa Decimal ovunque
            try:
                amount = Decimal(amount_str)
            except Exception:
                amount = Decimal("0")

            Expense.objects.create(
                project=project,
                date=date,
                category=category,
                vendor=vendor,
                amount=amount,
                note=note,
            )

            # aggiorna speso del progetto (opzionale, se “spent” è mantenuto manualmente)
            total_spent = Expense.objects.filter(project=project).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            project.spent = total_spent
            project.save(update_fields=["spent"])

            return redirect("project_detail", pk=project.pk)

        if action == "add_limit":
            limit_category = request.POST.get("limit_category")
            base = request.POST.get("base")  # BUDGET / SPENT / REMAINING
            perc_str = (request.POST.get("percentage") or "0").strip().replace(",", ".")
            try:
                percentage = Decimal(perc_str)
            except Exception:
                percentage = Decimal("0")

            SpendingLimit.objects.create(
                project=project,
                category=limit_category,
                base=base,
                percentage=percentage
            )
            return redirect("project_detail", pk=project.pk)

    # ---- GET: filtri spese
    cat = (request.GET.get("cat") or "").strip()
    vendor = (request.GET.get("vendor") or "").strip()

    exp_qs = Expense.objects.filter(project=project)
    if cat:
        exp_qs = exp_qs.filter(category=cat)
    if vendor:
        exp_qs = exp_qs.filter(vendor__icontains=vendor)

    expenses = exp_qs.order_by("-date", "-created_at")

    # ---- Limiti (tutta aritmetica in Decimal)
    budget = project.budget if project.budget is not None else Decimal("0")
    spent = project.spent if project.spent is not None else Decimal("0")
    remaining = budget - spent
    if remaining < Decimal("0"):
        remaining = Decimal("0")

    limits = SpendingLimit.objects.filter(project=project).order_by("category", "id")
    limits_table = []
    for lim in limits:
        # base
        if lim.base == "BUDGET":
            base_val = Decimal(budget)
            base_label = "Budget"
        elif lim.base == "SPENT":
            base_val = Decimal(spent)
            base_label = "Speso attuale"
        else:
            base_val = Decimal(remaining)
            base_label = "Residuo"

        # percentuale (Decimal) e calcoli
        perc = lim.percentage or Decimal("0")
        allowed = (base_val * (perc / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        used = Expense.objects.filter(project=project, category=lim.category).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        used = Decimal(used).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        remaining_limit = (allowed - used).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        limits_table.append({
            "limit": lim,
            "base_label": base_label,
            "allowed": allowed,
            "used": used,
            "remaining": remaining_limit,
        })

    return render(request, "projects/detail.html", {
        "project": project,
        "expenses": expenses,
        "categories": CATEGORIES,
        "limits_table": limits_table,
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
