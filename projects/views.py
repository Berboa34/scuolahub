from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, F, FloatField, Value, Case, When, Q
from django.http import HttpResponse, Http404
from .models import Project, School, Expense, SpendingLimit

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

    # filtro semplice per programma: ?program=PNRR/FESR/...
    program = request.GET.get("program", "").upper().strip()
    if program:
        qs = qs.filter(program=program)

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
        "program": program,
    })

@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(Project, pk=pk)

    # --- A) Gestione POST (crea spesa o limite)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_expense":
            Expense.objects.create(
                project=project,
                date=request.POST.get("date") or timezone.now().date(),
                vendor=request.POST.get("vendor") or "",
                category=request.POST.get("category") or "ALTRO",
                amount=Decimal(str(request.POST.get("amount", "0")).replace(",", ".")),
                document=request.POST.get("document") or "",
                note=request.POST.get("note") or "",
            )
            # opzionale: aggiorna il campo "spent" del progetto in base al totale reale
            totals = project.expenses.aggregate(total=Sum("amount"))
            project.spent = totals["total"] or Decimal("0")
            project.save(update_fields=["spent"])
            return redirect("project_detail", pk=project.pk)

        if action == "create_limit":
            SpendingLimit.objects.create(
                project=project,
                category=request.POST.get("category") or "MATERIALI",
                basis=request.POST.get("basis") or "TOTAL_SPENT",
                percentage=Decimal(str(request.POST.get("percentage", "0")).replace(",", ".")),
                note=request.POST.get("note") or "",
            )
            return redirect("project_detail", pk=project.pk)

    # --- B) Filtri GET su spese
    qs = project.expenses.all()
    category = request.GET.get("category") or ""
    vendor = request.GET.get("vendor") or ""
    if category:
        qs = qs.filter(category=category)
    if vendor:
        qs = qs.filter(vendor__icontains=vendor)

    expenses = qs.order_by("-date", "-id")
    agg_all = project.expenses.aggregate(total=Sum("amount"))
    total_spent = agg_all["total"] or Decimal("0")
    filtered_total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # progress % su budget
    progress_percent = Decimal("0")
    if project.budget and project.budget > 0:
        progress_percent = (total_spent * Decimal("100")) / project.budget
        if progress_percent > 100:
            progress_percent = Decimal("100")

    # --- C) Costruiamo contesto limiti senza filtri custom
    # somma spese per categoria
    by_cat = project.expenses.values("category").annotate(total=Sum("amount"))
    sums_by_cat = {row["category"]: row["total"] or Decimal("0") for row in by_cat}

    limits_ctx = []
    for lim in project.limits.all().order_by("category", "basis", "id"):
        # base per il calcolo
        if lim.basis == "TOTAL_SPENT":
            base_total = total_spent
            basis_label = "su Speso Totale"
        else:  # "TOTAL_BUDGET"
            base_total = project.budget or Decimal("0")
            basis_label = "su Budget"

        allowed_total = (lim.percentage / Decimal("100")) * base_total
        spent_in_cat = sums_by_cat.get(lim.category, Decimal("0"))
        remaining = allowed_total - spent_in_cat
        pct_used = Decimal("0")
        if allowed_total > 0:
            pct_used = (spent_in_cat * Decimal("100")) / allowed_total
            if pct_used > 100:
                pct_used = Decimal("100")

        limits_ctx.append({
            "category": lim.category,
            "category_label": dict(Expense.CATEGORY_CHOICES).get(lim.category, lim.category),
            "basis": lim.basis,
            "basis_label": dict(SpendingLimit.BASIS_CHOICES).get(lim.basis, lim.basis),
            "percentage": lim.percentage,
            "allowed_total": allowed_total,
            "spent_in_category": spent_in_cat,
            "remaining": remaining,
            "pct_used": pct_used,
        })

    context = {
        "project": project,
        "expenses": expenses,
        "filtered_total": filtered_total,
        "total_spent": total_spent,
        "progress_percent": progress_percent,
        "category_choices": Expense.CATEGORY_CHOICES,
        "basis_choices": SpendingLimit.BASIS_CHOICES,
        "add_expense": request.GET.get("add") == "expense",
        "add_limit": request.GET.get("add") == "limit",
        "limits_ctx": limits_ctx,
        "today": timezone.now().date().isoformat(),
    }
    return render(request, "projects/detail.html", context)

@login_required
def projects_by_school(request, school_id: int):
    school = get_object_or_404(School, pk=school_id)
    qs = Project.objects.filter(school=school)

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

    return render(request, "projects/projects_by_school.html", {
        "school": school, "projects": projects, "totals": totals
    })

@login_required
def db_check(request):
    qs = Project.objects.select_related("school").order_by("-start_date")
    rows = [f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}" for p in qs[:20]]
    html = "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    return HttpResponse(html)
