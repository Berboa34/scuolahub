from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, FloatField, Value, Case, When, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
import calendar
from django.urls import reverse

from .models import Project, School, Expense, SpendingLimit, Event, Delegation

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.mail import send_mail



@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    # Query di base dei progetti
    qs = Project.objects.all()
    if school:
        qs = qs.filter(school=school)

    # --- Totali globali ---
    # budget: somma dei budget dei progetti
    totals_budget = qs.aggregate(b=Sum("budget"))["b"] or Decimal("0")

    # spent: somma REALE delle Expense collegate ai progetti visibili
    totals_spent = (
        Expense.objects
        .filter(project__in=qs)
        .aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )

    totals = {
        "budget": totals_budget,
        "spent": totals_spent,
    }

    # --- Progetti in evidenza (ultimi 6) con "speso" calcolato dalle Expense ---
    latest = (
        qs.annotate(
            spent_from_expenses=Sum("expenses__amount")
        )
        .order_by("-start_date", "-id")[:6]
    )

    # Normalizziamo i None a 0
    for p in latest:
        p.spent_from_expenses = p.spent_from_expenses or Decimal("0")

    return render(
        request,
        "dashboard.html",
        {
            "school": school,
            "totals": totals,
            "latest": latest,
        },
    )


@login_required
def projects_list(request):
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    qs = Project.objects.all()
    if school:
        qs = qs.filter(school=school)

    # filtro per programma (GET ?program=PNRR, etc.)
    program = request.GET.get("program") or ""
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
        "program_selected": program,
    })


@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(Project, pk=pk)

    # Se l’utente è legato a una scuola, impediamo accesso ad altre scuole
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Progetto non trovato")

    # ---------------------------
    # A) Gestione POST (insert)
    # ---------------------------
    if request.method == "POST":
        op = request.POST.get("op", "")
        # A.1) Aggiungi spesa
        if op == "add_expense":
            try:
                date_str = request.POST.get("date") or timezone.now().date().isoformat()
                date_val = date_str  # field è DateField, Django lo parse in automatico se è 'YYYY-MM-DD'
                vendor = (request.POST.get("vendor") or "").strip() or None
                category = request.POST.get("category") or "ALTRO"
                amount_str = request.POST.get("amount") or "0"
                try:
                    amount = Decimal(amount_str)
                except (InvalidOperation, TypeError):
                    amount = Decimal("0")
                document = (request.POST.get("document") or "").strip() or None
                note = (request.POST.get("note") or "").strip() or None

                Expense.objects.create(
                    project=project,
                    date=date_val,
                    vendor=vendor,
                    category=category,
                    amount=amount,
                    document=document,
                    note=note,
                )
                # Post/Redirect/Get
                return redirect("project_detail", pk=project.pk)
            except Exception as e:
                return HttpResponseBadRequest(f"Errore inserimento spesa: {e}")

        # A.2) Aggiungi limite
        if op == "add_limit":
            try:
                category = request.POST.get("category") or "MATERIALI"
                base = request.POST.get("base") or "TOTAL_SPENT"   # <-- usa il campo 'base' (non 'basis')
                perc_str = request.POST.get("percentage") or "0"
                try:
                    percentage = Decimal(perc_str)
                except (InvalidOperation, TypeError):
                    percentage = Decimal("0")
                note = (request.POST.get("note") or "").strip() or None

                # unique_together = (project, category, base) — aggiorna se già esiste
                lim, created = SpendingLimit.objects.get_or_create(
                    project=project,
                    category=category,
                    base=base,
                    defaults={"percentage": percentage, "note": note},
                )
                if not created:
                    lim.percentage = percentage
                    lim.note = note
                    lim.save(update_fields=["percentage", "note"])

                return redirect("project_detail", pk=project.pk)
            except Exception as e:
                return HttpResponseBadRequest(f"Errore inserimento limite: {e}")

        # Se POST senza op valido
        return HttpResponseBadRequest("Operazione non riconosciuta.")

    # ---------------------------
    # B) Gestione GET (filtri)
    # ---------------------------
    exp_qs = project.expenses.all().order_by("-date", "-id")

    cat = request.GET.get("category") or ""
    if cat:
        exp_qs = exp_qs.filter(category=cat)

    vendor_q = request.GET.get("vendor") or ""
    if vendor_q:
        exp_qs = exp_qs.filter(vendor__icontains=vendor_q)

    expenses = list(exp_qs)
    filtered_total = exp_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Totale speso su tutte le spese del progetto
    total_spent = project.expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # Avanzamento (speso vs budget)
    budget = project.budget or Decimal("0")
    progress_percent = Decimal("0")
    if budget > 0:
        progress_percent = (total_spent * Decimal("100")) / budget
        if progress_percent > 100:
            progress_percent = Decimal("100")

    # ---------------------------
    # C) Limiti
    # ---------------------------
    by_cat = project.expenses.values("category").annotate(total=Sum("amount"))
    sums_by_cat = {row["category"]: row["total"] or Decimal("0") for row in by_cat}

    limits_ctx = []
    for lim in project.limits.all().order_by("category", "base", "id"):
        # lim.base: "TOTAL_SPENT" | "TOTAL_BUDGET"
        if lim.base == "TOTAL_SPENT":
            base_total = total_spent
        else:  # "TOTAL_BUDGET"
            base_total = budget

        allowed_total = (lim.percentage / Decimal("100")) * base_total
        spent_in_cat = sums_by_cat.get(lim.category, Decimal("0"))
        remaining = allowed_total - spent_in_cat

        pct_used = Decimal("0")
        if allowed_total > 0:
            pct_used = (spent_in_cat * Decimal("100")) / allowed_total
            if pct_used > 100:
                pct_used = Decimal("100")

        limits_ctx.append({
            "limit_id": lim.id,  # <<< AGGIUNTO: id vero dal model
            "category": lim.category,
            "category_label": dict(Expense.CATEGORY_CHOICES).get(lim.category, lim.category),
            "base": lim.base,
            "base_label": {
                "TOTAL_SPENT": "Percentuale sul totale speso",
                "TOTAL_BUDGET": "Percentuale sul budget totale"
            }.get(lim.base, lim.base),
            "percentage": lim.percentage,
            "allowed_total": allowed_total,
            "spent_in_category": spent_in_cat,
            "remaining": remaining,
            "pct_used": pct_used,
            "note": getattr(lim, "note", None),
        })

    context = {
        "project": project,
        "expenses": expenses,
        "filtered_total": filtered_total,
        "total_spent": total_spent,
        "progress_percent": progress_percent,
        "category_choices": Expense.CATEGORY_CHOICES,
        "base_choices": [("TOTAL_SPENT", "Percentuale sul totale speso"),
                         ("TOTAL_BUDGET", "Percentuale sul budget totale")],
        "add_expense": request.GET.get("add") == "expense",
        "add_limit": request.GET.get("add") == "limit",
        "limits_ctx": limits_ctx,
        "today": timezone.now().date().isoformat(),
    }
    return render(request, "projects/detail.html", context)


@login_required
def projects_by_school(request, school_id: int):
    # (opzionale: se non la usi più puoi rimuoverla e togliere la rotta)
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
def expense_delete(request, pk: int):
    """Elimina una singola spesa. URL: /spese/<pk>/elimina/ (POST)"""
    if request.method != "POST":
        return HttpResponseBadRequest("Metodo non consentito.")
    exp = get_object_or_404(Expense, pk=pk)
    project = exp.project

    # opzionale: blocco per scuola dell'utente
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Non autorizzato")

    exp.delete()
    return redirect("project_detail", pk=project.pk)

@login_required
def limit_delete(request, pk: int):
    """Elimina un limite di spesa. URL: /limiti/<pk>/elimina/ (POST)"""
    if request.method != "POST":
        return HttpResponseBadRequest("Metodo non consentito.")
    lim = get_object_or_404(SpendingLimit, pk=pk)
    project = lim.project

    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Non autorizzato")

    lim.delete()
    return redirect("project_detail", pk=project.pk)


@login_required
def limit_update(request, pk: int):
    """Modifica (base/percentage/category/note) di un limite. URL: /limiti/<pk>/modifica/ (POST)"""
    if request.method != "POST":
        return HttpResponseBadRequest("Metodo non consentito.")
    lim = get_object_or_404(SpendingLimit, pk=pk)
    project = lim.project

    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    if school and project.school_id and project.school_id != school.id:
        raise Http404("Non autorizzato")

    # Campi ammessi
    cat = request.POST.get("category") or lim.category
    base = request.POST.get("base") or lim.base
    perc_str = request.POST.get("percentage") or str(lim.percentage)
    note = (request.POST.get("note") or "").strip() or None

    try:
        lim.save()
    except Exception as e:
        # Fall-back: se confligge con un altro limite esistente, mostra errore semplice
        return HttpResponseBadRequest(f"Impossibile salvare il limite: {e}")

    return redirect("project_detail", pk=project.pk)


# (se ancora lo usi in urls per test rapido; altrimenti rimuovi anche la rotta)
@login_required
def db_check(request):
    qs = Project.objects.select_related("school").order_by("-start_date")
    rows = [f"{p.id} • {p.title} • {p.school.name if p.school_id else '-'}" for p in qs[:20]]
    html = "OK DB — Projects: %d<br>%s" % (qs.count(), "<br>".join(rows) or "— nessun progetto —")
    return HttpResponse(html)

@login_required
def calendar_view(request):
    """
    Calendario mensile:
    - ogni utente vede i propri eventi (owner = request.user)
    - facoltativamente filtrati per scuola (profile.school)
    """
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    today = timezone.localdate()

    # anno / mese dai parametri, altrimenti mese corrente
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except ValueError:
        year, month = today.year, today.month

    # --- A) Se POST: aggiungo un nuovo evento
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        date_str = request.POST.get("date")
        description = (request.POST.get("description") or "").strip()
        project_id = request.POST.get("project_id") or None  # ← IMPORTANTE: NOME CAMPO

        if title and date_str:
            try:
                ev_date = date.fromisoformat(date_str)
            except ValueError:
                ev_date = today

            project = None
            if project_id:
                try:
                    project = Project.objects.get(pk=project_id)
                except Project.DoesNotExist:
                    project = None

            Event.objects.create(
                school=school or (project.school if project else None),
                project=project,
                owner=request.user,
                title=title,
                description=description,
                date=ev_date,
            )

        return redirect(f"{reverse('calendar')}?year={year}&month={month}")

    # --- B) Intervallo del mese
    first_day = date(year, month, 1)
    _, last_day_num = calendar.monthrange(year, month)
    last_day = date(year, month, last_day_num)

    # Eventi dell'utente nel mese
    events_qs = Event.objects.filter(
        owner=request.user,
        date__gte=first_day,
        date__lte=last_day,
    )
    if school:
        events_qs = events_qs.filter(school=school)

    events_by_day = {}
    for ev in events_qs.select_related("project"):
        events_by_day.setdefault(ev.date, []).append(ev)

    cal = calendar.Calendar(firstweekday=0)
    weeks = []
    week = []
    for d in cal.itermonthdates(year, month):
        cell = {
            "date": d,
            "in_month": (d.month == month),
            "events": events_by_day.get(d, []),
            "is_today": (d == today),
        }
        week.append(cell)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        weeks.append(week)

    # Mese precedente / successivo
    prev_month_date = (first_day - timedelta(days=1)).replace(day=1)
    next_month_date = (last_day + timedelta(days=1)).replace(day=1)

    months_it = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
    ]
    month_label = f"{months_it[month - 1]} {year}"

    # Progetti della scuola / tutti
    projects_qs = Project.objects.all()
    if school:
        projects_qs = projects_qs.filter(school=school)

    context = {
        "school": school,
        "weeks": weeks,
        "month_label": month_label,
        "year": year,
        "month": month,
        "prev_year": prev_month_date.year,
        "prev_month": prev_month_date.month,
        "next_year": next_month_date.year,
        "next_month": next_month_date.month,
        "projects": projects_qs.order_by("title"),  # ← QUI PASSIAMO I PROGETTI
        "today": today,
    }
    return render(request, "calendar.html", context)


@login_required
def deleghe_view(request):
    """
    Gestione deleghe (versione semplificata):
    - Collaboratori: tutti gli utenti del sistema
    - Progetti: tutti i progetti
    - Deleghe visualizzate: quelle che ho dato e quelle che ho ricevuto
    """
    User = get_user_model()

    # --- Collaboratori: TUTTI gli utenti (nessun filtro / exclude)
    collaborators = User.objects.all().order_by("username")

    # --- Progetti: TUTTI i progetti
    projects_qs = Project.objects.all().order_by("title")

    # --- Creazione nuova delega via POST
    if request.method == "POST":
        to_user_id = request.POST.get("to_user")
        title = (request.POST.get("title") or "").strip()
        scope = (request.POST.get("scope") or "").strip()
        project_id = request.POST.get("project_id") or None
        start_str = request.POST.get("start_date") or ""
        end_str = request.POST.get("end_date") or ""

        if to_user_id and title:
            to_user = get_object_or_404(User, pk=to_user_id)

            project = None
            if project_id:
                try:
                    project = Project.objects.get(pk=project_id)
                except Project.DoesNotExist:
                    project = None

            start_date = None
            end_date = None
            try:
                if start_str:
                    start_date = date.fromisoformat(start_str)
                if end_str:
                    end_date = date.fromisoformat(end_str)
            except ValueError:
                pass

            # NOTA: school qui non è obbligatorio; se il modello Delegation ha school, puoi passare project.school se esiste
            school = getattr(project, "school", None) if project else None

            Delegation.objects.create(
                school=school,
                project=project,
                from_user=request.user,
                to_user=to_user,
                title=title,
                scope=scope,
                start_date=start_date,
                end_date=end_date,
                is_active=True,
            )

        return redirect(reverse("deleghe"))

    # --- Deleghe che ho dato io
    deleghe_give = (
        Delegation.objects.filter(from_user=request.user)
        .select_related("to_user", "project", "school")
        .order_by("-created_at")
    )

    # --- Deleghe che ho ricevuto
    deleghe_receive = (
        Delegation.objects.filter(to_user=request.user)
        .select_related("from_user", "project", "school")
        .order_by("-created_at")
    )

    context = {
        "collaborators": collaborators,
        "projects": projects_qs,
        "deleghe_give": deleghe_give,
        "deleghe_receive": deleghe_receive,
    }
    return render(request, "deleghe.html", context)


@login_required
def delegation_revoke(request, pk: int):
    """
    Revoca una delega: la segniamo come non attiva.
    (Non la cancelliamo dal DB, così rimane traccia storica.)
    """
    delega = get_object_or_404(Delegation, pk=pk)

    # Per sicurezza, permetti la revoca solo a chi l'ha creata o a staff
    if delega.from_user != request.user and not request.user.is_staff:
        return redirect("deleghe")

    if request.method == "POST":
        delega.is_active = False
        delega.save(update_fields=["is_active"])
        return redirect("deleghe")

    return redirect("deleghe")



@login_required
def event_delete(request, pk: int):
    """
    Elimina un evento dal calendario.
    Per ora NON controlliamo l'owner dell'evento, perché il modello Event
    non ha ancora un campo 'user'. Qualsiasi utente autenticato può eliminare.
    """
    event = get_object_or_404(Event, pk=pk)

    if request.method == "POST":
        event.delete()
        return redirect("calendar")

    # Se qualcuno arriva in GET, lo rimandiamo comunque al calendario
    return redirect("calendar")
