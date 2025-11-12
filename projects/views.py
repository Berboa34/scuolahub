from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Project, Expense, SpendingLimit
from .models import Project, Expense, SpendingLimit, School

@login_required

def projects_by_school(request, school_id: int):
    school = get_object_or_404(School, pk=school_id)
    projects = Project.objects.filter(school=school).order_by("title", "id")
    return render(request, "projects/by_school.html", {
        "school": school,
        "projects": projects,
    })

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

    # percentuale spesa calcolata lato template usando budget/spent
    projects = qs.order_by("title", "id")

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

    # --- A) POST (creazione spesa o limite)
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
            totals = project.expenses.aggregate(total=Sum("amount"))
            project.spent = totals["total"] or Decimal("0")
            project.save(update_fields=["spent"])
            return redirect("project_detail", pk=project.pk)

        if action == "create_limit":
            # NOME CAMPO CORRETTO: base (NON basis)
            SpendingLimit.objects.create(
                project=project,
                category=request.POST.get("category") or "MATERIALI",
                base=request.POST.get("base") or "TOTAL_SPENT",
                percentage=Decimal(str(request.POST.get("percentage", "0")).replace(",", ".")),
                note=request.POST.get("note") or "",
            )
            return redirect("project_detail", pk=project.pk)

    # --- B) Filtri sulle spese
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

    # --- C) Limiti di spesa per categoria ---
    by_cat = project.expenses.values("category").annotate(total=Sum("amount"))
    sums_by_cat = {row["category"]: row["total"] or Decimal("0") for row in by_cat}

    limits_ctx = []
    for lim in project.limits.all().order_by("category", "base", "id"):
        # Determina base di calcolo
        if lim.base == "TOTAL_SPENT":
            base_total = total_spent
            base_label = "Percentuale sul totale speso"
        else:  # TOTAL_BUDGET
            base_total = project.budget or Decimal("0")
            base_label = "Percentuale sul budget totale"

        # Calcolo importi
        allowed_total = (lim.percentage / Decimal("100")) * base_total
        spent_in_cat = sums_by_cat.get(lim.category, Decimal("0"))
        remaining = allowed_total - spent_in_cat
        remaining_abs = abs(remaining)

        # Percentuale utilizzata
        pct_used = Decimal("0")
        if allowed_total > 0:
            pct_used = (spent_in_cat * Decimal("100")) / allowed_total
            if pct_used > 100:
                pct_used = Decimal("100")

        # Costruzione contesto
        limits_ctx.append({
            "category": lim.category,
            "category_label": dict(Expense.CATEGORY_CHOICES).get(lim.category, lim.category),
            "base": lim.base,
            "base_label": base_label,
            "percentage": lim.percentage,
            "allowed_total": allowed_total,
            "spent_in_category": spent_in_cat,
            "remaining": remaining,
            "remaining_abs": remaining_abs,  # usato nel template al posto di |abs
            "pct_used": pct_used,
        })

    # Context finale
    context = {
        "project": project,
        "expenses": expenses,
        "filtered_total": filtered_total,
        "total_spent": total_spent,
        "progress_percent": progress_percent,
        "category_choices": Expense.CATEGORY_CHOICES,
        "base_choices": [
            ("TOTAL_SPENT", "Percentuale sul totale speso"),
            ("TOTAL_BUDGET", "Percentuale sul budget totale"),
        ],
        "add_expense": request.GET.get("add") == "expense",
        "add_limit": request.GET.get("add") == "limit",
        "limits_ctx": limits_ctx,
        "today": timezone.now().date().isoformat(),
    }
    return render(request, "projects/detail.html", context)

