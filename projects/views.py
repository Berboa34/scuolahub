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
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Progetto non trovato")

    # Gestione form aggiunta spesa
    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "add_expense":
            try:
                amount = Decimal((request.POST.get("amount") or "0").replace(",", "."))
            except InvalidOperation:
                amount = Decimal("0")
            Expense.objects.create(
                project=project,
                date=request.POST.get("date") or None,
                vendor=request.POST.get("vendor") or "",
                category=request.POST.get("category") or "ALTRO",
                amount=amount,
                document=request.POST.get("document") or "",
                note=request.POST.get("note") or "",
            )
            # riallineo spesa aggregata del progetto
            agg = project.expenses.aggregate(total=Sum("amount"))
            project.spent = agg["total"] or 0
            project.save(update_fields=["spent"])
            return redirect("project_detail", pk=project.pk)

        if action == "add_limit":
            basis = request.POST.get("basis") or "TOTAL_SPENT"
            category = request.POST.get("category") or "MATERIALI"
            try:
                percentage = Decimal((request.POST.get("percentage") or "0").replace(",", "."))
            except InvalidOperation:
                percentage = Decimal("0")
            SpendingLimit.objects.update_or_create(
                project=project,
                category=category,
                basis=basis,
                defaults={"percentage": percentage, "note": request.POST.get("note") or ""},
            )
            return redirect("project_detail", pk=project.pk)

    # Dati per calcolo limiti
    totals = project.__class__.objects.filter(pk=project.pk).aggregate(
        budget=Sum("budget"), spent=Sum("spent")
    )
    totals["budget"] = totals["budget"] or Decimal("0")
    totals["spent"] = totals["spent"] or Decimal("0")

    # Applico i limiti (basis, non base!)
    limits = list(project.limits.all())
    computed_limits = []
    for lim in limits:
        if lim.basis == "TOTAL_SPENT":
            base_value = totals["spent"]
        else:
            base_value = totals["budget"]
        allowed = (base_value * lim.percentage) / Decimal("100")
        used = project.expenses.filter(category=lim.category).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        remaining = allowed - used
        computed_limits.append({
            "obj": lim,
            "base_value": base_value,
            "allowed": allowed,
            "used": used,
            "remaining": remaining,
        })

    expenses = project.expenses.order_by("-date", "-id")

    return render(request, "projects/detail.html", {
        "project": project,
        "expenses": expenses,
        "limits": computed_limits,
        "totals": totals,
    })

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
