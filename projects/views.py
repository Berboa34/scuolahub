from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, F, FloatField, Value, Case, When
from django.http import HttpResponse, Http404

from .models import Project, School


@login_required
def dashboard(request):
    """
    Home protetta: mostra KPI aggregati e liste progetti, filtrando (se presente)
    per la scuola associata al profilo dell'utente.
    """
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    qs = Project.objects.all()
    if school:
        qs = qs.filter(school=school)

    totals = qs.aggregate(budget=Sum("budget"), spent=Sum("spent"))
    totals["budget"] = totals["budget"] or 0
    totals["spent"] = totals["spent"] or 0

    latest = qs.order_by("-start_date")[:6]
    projects = qs.annotate(
        percent_spent=Case(
            When(budget__gt=0, then=100.0 * F("spent") / F("budget")),
            default=Value(0.0),
            output_field=FloatField(),
        )
    ).order_by("title", "id")

    return render(
        request,
        "dashboard.html",
        {
            "school": school,
            "totals": totals,
            "latest": latest,
            "projects": projects,
        },
    )


@login_required
def project_detail(request, pk: int):
    """
    Dettaglio progetto. Se l'utente ha una scuola associata, impedisce di vedere
    progetti di altre scuole (404).
    """
    project = get_object_or_404(Project, pk=pk)

    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Progetto non trovato")

    return render(request, "project_detail.html", {"project": project})


@login_required
def projects_by_school(request, school_id: int):
    """
    Lista progetti per una scuola specifica (rotta: /scuole/<id>/progetti/).
    Utile anche come pagina filtro.
    """
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

    return render(
        request,
        "projects_by_school.html",  # crea questo template se non esiste
        {"school": school, "projects": projects, "totals": totals},
    )


@login_required
def db_check(request):
    """
    Endpoint di debug per verificare la connettività al DB e i primi record.
    Rotta: /debug/db/
    """
    qs = Project.objects.select_related("school").order_by("-start_date")
    rows = [
        f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}"
        for p in qs[:20]
    ]
    html = "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    return HttpResponse(html)
