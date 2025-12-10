from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, FloatField, Value, Case, When, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
import calendar
from django.urls import reverse
from django.db import transaction

from django.contrib import messages
from django.conf import settings

from .models import Project, School, Expense, SpendingLimit, Event, Delegation, Milestone, ExpenseCategory

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import School, Document, CallForProposal, Call, Notification


User = get_user_model()




@login_required
def dashboard(request):
    """
    Dashboard:
    - KPI budget/spesa calcolati sui progetti della scuola
    - Progetti recenti con speso calcolato dalle Expense
    - Notifiche per l'utente loggato
    - Prossimi eventi di calendario per l'utente
    """
    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)

    # --- PROGETTI DELLA SCUOLA
    projects_qs = Project.objects.all()
    if school:
        projects_qs = projects_qs.filter(school=school)

    # KPI: budget totale e spesa totale (somma delle Expense)
    totals = {}
    totals["budget"] = projects_qs.aggregate(b=Sum("budget"))["b"] or 0

    expenses_qs = Expense.objects.filter(project__in=projects_qs)
    totals["spent"] = expenses_qs.aggregate(s=Sum("amount"))["s"] or 0

    # Progetti recenti (ultimi 6) con spesa calcolata dalle expense
    latest = list(projects_qs.order_by("-start_date", "-id")[:6])

    # Mappa project.id -> somma spese
    sums_per_project = (
        Expense.objects
        .filter(project__in=latest)
        .values("project_id")
        .annotate(total=Sum("amount"))
    )
    sums_map = {row["project_id"]: row["total"] or 0 for row in sums_per_project}

    for p in latest:
        # attributo usato nel template
        p.spent_from_expenses = sums_map.get(p.id, 0)

    # --- NOTIFICHE PER L'UTENTE
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:5]

    # --- PROSSIMI EVENTI (CALENDARIO)
    today = timezone.localdate()
    events_qs = Event.objects.filter(owner=request.user, date__gte=today)
    if school:
        events_qs = events_qs.filter(school=school)
    upcoming_events = events_qs.order_by("date")[:5]

    context = {
        "school": school,
        "totals": totals,
        "latest": latest,
        "notifications": notifications,
        "upcoming_events": upcoming_events,
    }
    return render(request, "dashboard.html", context)




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


from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, FloatField, Value, Case, When, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
import calendar
from django.urls import reverse
from django.db import transaction

from django.contrib import messages
from django.conf import settings

# Assicurati di importare tutti i modelli necessari qui, inclusa Milestone
from .models import Project, School, Expense, SpendingLimit, Event, Delegation, Milestone

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import School, Document, CallForProposal, Call, Notification


# ... (Il resto degli import e delle funzioni sono invariati) ...

@login_required
def project_detail(request, pk: int):
    today = timezone.localdate()  # Utilizzo coerente della data odierna
    project = get_object_or_404(Project, pk=pk)
    project_pk = project.pk

    profile = getattr(request.user, "profile", None)
    school = getattr(profile, "school", None)
    is_superuser = request.user.is_superuser

    if school and project.school_id and project.school_id != school.id and not is_superuser:
        raise Http404("Progetto non trovato")

    # --- ACQUISIZIONE CATEGORIE DINAMICHE ---
    if school:
        valid_categories = ExpenseCategory.objects.filter(school=school).order_by('name')
    else:
        valid_categories = ExpenseCategory.objects.all().order_by('name')

    # Crea la lista di choices (PK, Nome) per l'uso nei form HTML
    category_choices = [(cat.pk, cat.name) for cat in valid_categories]

    # ---------------------------
    # A) Gestione POST (insert) - Aggiornato per Foreign Key
    # ---------------------------
    if request.method == "POST":
        op = request.POST.get("op", "")

        # A.1) Aggiungi spesa
        if op == "add_expense":
            try:
                date_str = request.POST.get("date") or today.isoformat()
                date_val = date_str
                vendor = (request.POST.get("vendor") or "").strip() or None
                category_pk = request.POST.get("category")  # Recupera l'ID
                amount_str = request.POST.get("amount") or "0"
                amount = Decimal(amount_str)
                document = (request.POST.get("document") or "").strip() or None
                note = (request.POST.get("note") or "").strip() or None

                if not category_pk:
                    raise ValueError("Categoria di Spesa è obbligatoria.")
                category_obj = get_object_or_404(ExpenseCategory, pk=category_pk)

                Expense.objects.create(
                    project=project, date=date_val, vendor=vendor,
                    category=category_obj,  # Usa l'oggetto ExpenseCategory
                    amount=amount, document=document, note=note,
                )
                messages.success(request, "Spesa aggiunta con successo.")
                return redirect("project_detail", pk=project_pk)
            except Exception as e:
                messages.error(request, f"Errore inserimento spesa: {e}")
                return redirect(f"{reverse('project_detail', args=[project_pk])}?add=expense")

        # A.2) Aggiungi limite
        if op == "add_limit":
            try:
                category_pk = request.POST.get("category")  # Recupera l'ID
                base = request.POST.get("base") or "TOTAL_BUDGET"
                perc_str = request.POST.get("percentage") or "0"
                percentage = Decimal(perc_str)
                note = (request.POST.get("note") or "").strip() or None

                if not category_pk:
                    raise ValueError("Categoria di Spesa è obbligatoria.")
                category_obj = get_object_or_404(ExpenseCategory, pk=category_pk)

                lim, created = SpendingLimit.objects.get_or_create(
                    project=project, category=category_obj, base=base,  # Usa l'oggetto ExpenseCategory
                    defaults={"percentage": percentage, "note": note},
                )
                if not created:
                    lim.percentage = percentage
                    lim.note = note
                    lim.save(update_fields=["percentage", "note"])

                messages.success(request, "Limite aggiornato con successo.")
                return redirect("project_detail", pk=project_pk)
            except Exception as e:
                messages.error(request, f"Errore inserimento limite: {e}")
                return redirect(f"{reverse('project_detail', args=[project_pk])}?add=limit")

        # A.3) Aggiungi Milestone (Logica invariata)
        if op == "add_milestone":
            try:
                title = (request.POST.get("title") or "").strip()
                due_date_str = request.POST.get("due_date")
                status = request.POST.get("status") or "PENDING"
                description = (request.POST.get("description") or "").strip() or None

                if not title or not due_date_str:
                    raise ValueError("Titolo e Data di Scadenza sono obbligatori.")

                Milestone.objects.create(
                    project=project, title=title, due_date=due_date_str, status=status, description=description,
                )
                messages.success(request, f"Milestone '{title}' aggiunta con successo.")
                return redirect("project_detail", pk=project_pk)
            except Exception as e:
                messages.error(request, f"Errore inserimento milestone: {e}")
                return redirect(f"{reverse('project_detail', args=[project_pk])}?add=milestone")

        # Se POST senza op valido
        return HttpResponseBadRequest("Operazione non riconosciuta.")

    # ---------------------------
    # B) Gestione GET (Calcoli Finanziari) - Aggiornato il filtro categoria
    # ---------------------------
    # select_related('category') ottimizza il recupero del nome della categoria nella lista spese.
    exp_qs = project.expenses.all().order_by("-date", "-id")

    cat_pk = request.GET.get("category") or ""
    current_category = None  # Variabile per mantenere il filtro selezionato nel template
    if cat_pk:
        try:
            cat_pk = int(cat_pk)
            exp_qs = exp_qs.filter(category__pk=cat_pk)
            current_category = cat_pk
        except ValueError:
            pass  # Ignora se non è un ID intero valido

    vendor_q = request.GET.get("vendor") or ""
    if vendor_q: exp_qs = exp_qs.filter(vendor__icontains=vendor_q)

    expenses = list(exp_qs)
    filtered_total = exp_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    total_spent = project.expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    budget = project.budget or Decimal("0")
    progress_percent = Decimal("0")
    if budget > 0:
        progress_percent = (total_spent * Decimal("100")) / budget
        if progress_percent > 100: progress_percent = Decimal("100")

    # ---------------------------
    # C) Limiti - Aggiornata la query di raggruppamento e il contesto
    # ---------------------------
    # Raggruppa per la chiave che Django vede: 'category' (non 'category_id')
    by_cat = project.expenses.values("category").annotate(total=Sum("amount"))

    # Mappa le somme alla chiave 'category' (che è l'ID)
    sums_by_id = {row["category"]: row["total"] or Decimal("0") for row in by_cat}

    limits_ctx = []
    # RIMOSSO .select_related() per evitare ambiguità, ordina per 'base' semplice
    for lim in project.limits.all().order_by("base"):

        # 🚨 GESTIONE DATI IBRIDI E NON MIGRATI
        try:
            # Tenta di accedere all'oggetto Foreign Key e ai suoi attributi
            category_pk = lim.category.pk
            category_name = lim.category.name
        except AttributeError:
            # Se lim.category non è un oggetto ExpenseCategory (es. è NULL o una stringa vecchia non migrata)
            # Sostituiamo con valori di fallback sicuri per non bloccare la pagina
            category_pk = None
            category_name = "Categoria Non Trovata/Errore"
            # Per la logica di spesa, skippiamo il calcolo se la categoria non è valida
            spent_in_cat = Decimal("0")
        except Exception:
            category_pk = None
            category_name = "Categoria Non Trovata/Errore"
            spent_in_cat = Decimal("0")

        if category_pk is not None:
            # Se la categoria è valida, usa l'ID per trovare la spesa aggregata
            spent_in_cat = sums_by_id.get(category_pk, Decimal("0"))

        base_total = total_spent if lim.base == "TOTAL_SPENT" else budget
        allowed_total = (lim.percentage / Decimal("100")) * base_total
        remaining = allowed_total - spent_in_cat

        pct_used = Decimal("0")
        if allowed_total > 0:
            pct_used = (spent_in_cat * Decimal("100")) / allowed_total
            if pct_used > 100: pct_used = Decimal("100")

        limits_ctx.append({
            "limit_id": lim.id,
            "category": category_pk,
            "category_label": category_name,
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

    # ---------------------------
    # D) Milestone (Logica invariata per la timeline)
    # ---------------------------
    milestones = project.milestones.all().order_by('due_date')

    project_start = project.start_date
    project_end = project.end_date
    today_pos_percent = None

    if project_start and project_end and project_end > project_start:
        time_span = project_end - project_start
        total_days = float(time_span.days)

        if total_days > 0:
            days_passed_td = today - project_start
            days_passed_today = days_passed_td.days
            raw_percent = (float(days_passed_today) / total_days) * 100
            today_pos_percent = min(100, max(0, raw_percent))

            for ms in milestones:
                if ms.due_date:
                    ms_time_span = ms.due_date - project_start
                    ms_days_from_start = ms_time_span.days
                    ms_raw_percent = (float(ms_days_from_start) / total_days) * 100
                    ms.pos_percent = min(100, max(0, ms_raw_percent))
                else:
                    ms.pos_percent = None
        else:
            today_pos_percent = 0
            for ms in milestones: ms.pos_percent = 0
    else:
        today_pos_percent = None
        for ms in milestones: ms.pos_percent = None

    total_milestones = milestones.count()
    completed_milestones = milestones.filter(status='COMPLETED').count()
    milestone_progress_percent = Decimal("0")
    if total_milestones > 0:
        milestone_progress_percent = (completed_milestones * Decimal("100")) / total_milestones

    # ---------------------------
    # E) Context completo
    # ---------------------------
    context = {
        "project": project,
        "expenses": expenses,
        "filtered_total": filtered_total,
        "total_spent": total_spent,
        "progress_percent": progress_percent,
        "category_choices": category_choices,  # LISTA DINAMICA
        "base_choices": [("TOTAL_SPENT", "Percentuale sul totale speso"),
                         ("TOTAL_BUDGET", "Percentuale sul budget totale")],
        "add_expense": request.GET.get("add") == "expense",
        "add_limit": request.GET.get("add") == "limit",
        "add_milestone": request.GET.get("add") == "milestone",
        "limits_ctx": limits_ctx,

        "milestones": milestones,
        "milestone_progress_percent": milestone_progress_percent,
        "completed_milestones": completed_milestones,
        "total_milestones": total_milestones,

        "project_start": project_start,
        "project_end": project_end,
        "today_pos_percent": today_pos_percent,
        "today": today.isoformat(),
        "current_category": current_category,  # ID della categoria selezionata per il filtro
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


from datetime import date, timedelta
import calendar
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Project, Expense, SpendingLimit, Event, Delegation
from django.utils import timezone





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


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse



@login_required
def documents_view(request):
    """
    Gestione documenti condivisi.
    - Mostra tutti i documenti caricati
    - Permette di caricare un nuovo documento
    - Permette di collegare (opzionale) un progetto
    - is_final: se spuntato, il documento è 'definitivo' (non modificabile dalla UI)
    """
    # Progetti disponibili nel menu a tendina: TUTTI i progetti
    projects_qs = Project.objects.all().order_by("title")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        project_id = request.POST.get("project_id") or None
        is_final = bool(request.POST.get("is_final"))
        uploaded_file = request.FILES.get("file")

        project = None
        if project_id:
            project = Project.objects.filter(pk=project_id).first()

        if title and uploaded_file:
            Document.objects.create(
                title=title,
                file=uploaded_file,
                project=project,
                uploaded_by=request.user,
                is_final=is_final,
            )

        # Sempre redirect per evitare il repost del form
        return redirect("documents")

    # Lista documenti
    documents_qs = Document.objects.select_related("project", "uploaded_by")

    projects_qs = Project.objects.all().order_by("title")

    context = {
        "documents": documents_qs,
        "projects": projects_qs,
    }
    return render(request, "documents.html", context)


@login_required
def document_delete(request, pk: int):
    """
    Elimina un documento caricato.
    (Per ora non controlliamo ruoli: qualsiasi utente autenticato può eliminare.)
    """
    doc = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        doc.delete()
        return redirect("documents")

    return redirect("documents")



@login_required
@user_passes_test(lambda u: u.is_staff)
def document_finalize(request, pk: int):
    """
    L'amministratore può marcare un documento come DEFINITIVO.
    Da qui in poi in piattaforma non è più modificabile.
    (In admin volendo si può comunque intervenire, ma per il mockup va bene così.)
    """
    doc = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        doc.status = "FINAL"
        doc.save(update_fields=["status"])
    return redirect("documents")


def is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(is_superuser, login_url='/accounts/login/')
def deleghe_view(request):
    """
    Gestione deleghe (solo admin):
    - crea una delega collegando un collaboratore a un progetto
    - crea una NOTIFICA legata alla delega per il collaboratore
    """
    User = get_user_model()

    projects = Project.objects.all().order_by("title")
    collaborators = User.objects.filter(is_active=True).order_by("username")
    #deleghe = Delegation.objects.select_related("project", "collaborator").order_by("-created_at")
    deleghe = Delegation.objects.all().order_by("-created_at")

    if request.method == "POST" and request.POST.get("op") == "add_delegation":
        project_id = request.POST.get("project_id")
        collaborator_id = request.POST.get("collaborator_id")
        role_label = (request.POST.get("role_label") or "").strip()
        note = (request.POST.get("note") or "").strip()

        if project_id and collaborator_id:
            try:
                project = get_object_or_404(Project, pk=project_id)
                collaborator = get_object_or_404(User, pk=collaborator_id)

                # 1) creo la DELEGA con stato PENDING e nota salvata
                delega = Delegation.objects.create(
                    project=project,
                    collaborator=collaborator,
                    role_label=role_label,
                    note=note,
                    status="PENDING",
                    creator=request.user,
                )

                # 2) creo la NOTIFICA AGGANCIATA alla delega
                Notification.objects.create(
                    user=collaborator,
                    message=f"Ti è stata assegnata una delega sul progetto '{project.title}'.",
                    delegation=delega,
                )

                messages.success(
                    request,
                    f"Delega per {collaborator.username} sul progetto “{project.title}” creata e notifica registrata."
                )
            except Exception as e:
                messages.error(request, f"Errore durante il salvataggio della delega: {e}")
        else:
            messages.error(request, "Seleziona un progetto e un collaboratore.")

        return redirect("deleghe")

    context = {
        "projects": projects,
        "collaborators": collaborators,
        "deleghe": deleghe,
    }
    return render(request, "deleghe.html", context)



# ----------------------------------------------------------------------
# VISTA PER ELIMINAZIONE DELEGA (associata a deleghe/<int:pk>/elimina/)
# ----------------------------------------------------------------------

@login_required
@user_passes_test(is_superuser, login_url='/accounts/login/')
def delegation_delete(request, pk):
    # La logica del tuo urls.py richiede che questa vista sia un POST per eliminare
    delegation = get_object_or_404(Delegation, pk=pk)
    if request.method == 'POST':
        # Optional: Aggiungere qui un controllo di sicurezza in più
        delegation.delete()
        messages.success(request, "Delega eliminata con successo.")
    return redirect('deleghe')


@login_required
def my_delegations_view(request):
    # Filtra solo le deleghe dove l'utente loggato è il collaboratore
    my_deleghe = Delegation.objects.filter(collaborator=request.user).select_related('project')

    # Prepara un template specifico o usa deleghe.html in modalità lettura
    context = {
        'deleghe': my_deleghe,
        'is_collaborator_view': True,  # Variabile per disabilitare il form di creazione nel template
    }

    # Dovrai creare un template my_delegations.html o adattare deleghe.html
    return render(request, 'my_delegations.html', context)




@login_required
def delegation_confirm(request, pk):
    delegation = get_object_or_404(Delegation, pk=pk)

    # Sicurezza: solo il collaboratore assegnato può confermare
    if delegation.collaborator != request.user:
        messages.error(request, "Non sei autorizzato a modificare questa delega.")
        return redirect('my_delegations')

    if request.method == 'POST':
        delegation.status = "CONFIRMED"  # O "ACTIVE", a seconda della tua logica
        delegation.save()
        messages.success(request, f"Delega per {delegation.project.title} confermata.")

    return redirect('my_delegations')


@login_required
def bando_detail(request, pk: int):
    call = get_object_or_404(Call, pk=pk)

    return render(request, "calls/detail.html", {
        "call": call,
    })



from django.db.models import Q
from .models import Call

@login_required
def bandi_list(request):
    """
    Elenco bandi/call:
    - filtro per programma
    - filtro per stato
    - ricerca testuale su titolo / fonte / tag
    """
    qs = Call.objects.all().order_by("deadline", "title")

    program = request.GET.get("program") or ""
    status = request.GET.get("status") or ""
    q = (request.GET.get("q") or "").strip()

    if program:
        qs = qs.filter(program=program)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(source__icontains=q) |
            Q(tags__icontains=q)
        )

    context = {
        "calls": qs,
        "PROGRAM_CHOICES": Call.PROGRAM_CHOICES,
        "STATUS_CHOICES": Call.STATUS_CHOICES,
        "selected_program": program,
        "selected_status": status,
        "search_query": q,
    }
    return render(request, "calls/list.html", context)

@login_required
def notification_read(request, pk: int):
    """
    Mostra il dettaglio di una notifica e la segna come letta.
    Solo il proprietario (o il superuser) può vederla.
    """
    notif = get_object_or_404(Notification, pk=pk)

    # sicurezza: solo il proprietario o superuser
    if notif.user != request.user and not request.user.is_superuser:
        return redirect("dashboard")

    # se non è ancora letta, segna come letta
    if not notif.is_read:
        notif.is_read = True
        notif.save()

    return render(request, "notification_detail.html", {
        "notification": notif,
    })



from django.http import HttpResponseForbidden


@login_required
def notification_detail(request, pk: int):
    """
    Mostra i dettagli di una notifica e gestisce l'accettazione/rifiuto della delega collegata.
    """

    # 1. Recupero notifica (filtrata anche per l'utente, per sicurezza)
    # Assicurati che l'utente loggato sia il destinatario
    notification = get_object_or_404(
        Notification.objects.filter(user=request.user),
        pk=pk
    )

    # 2. Recupera la DELEGA COLLEGATA
    # Se il link esiste nel database, questo recupera l'oggetto.
    delegation = notification.delegation  # <--- QUESTA RIGA DEVE ESSERE ESEGUITA

    # 3. Aggiorna lo stato "letto"
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    # 4. Prepara le variabili di controllo (can_accept/can_reject)
    can_accept = False
    can_reject = False

    # I pulsanti sono attivi solo se la delega esiste, lo stato è PENDING e l'utente è il delegato
    if delegation and delegation.status == "PENDING" and request.user == delegation.collaborator:
        can_accept = True
        can_reject = True

    # 5. GESTIONE POST (Accetta/Rifiuta)
    if request.method == "POST" and delegation is not None:
        action = request.POST.get("action")

        admin_recipient = delegation.creator
        user_collaborator = request.user



        if action == "accept" and can_accept:
            delegation.status = "CONFIRMED"
            delegation.save(update_fields=["status"])


            # 2. NOTIFICA ALL'ADMIN
            Notification.objects.create(
                user=admin_recipient,  # Usa il nome pulito
                message=f"✅ La delega per '{delegation.project.title}' è stata **ACCETTATA** dal professore {user_collaborator.username}.",
                delegation=delegation,
            )

            messages.success(request, "Hai accettato la delega.")
            # Crea notifica di risposta all'Admin qui...
            return redirect("dashboard")

        if action == "reject" and can_reject:
            delegation.status = "REJECTED"
            delegation.save(update_fields=["status"])


            # 2. NOTIFICA ALL'ADMIN
            Notification.objects.create(
                user=admin_recipient,
                message=f"❌ La delega per '{delegation.project.title}' è stata **RIFIUTATA** dal professore {user_collaborator.username}.",
                delegation=delegation,
            )

            messages.success(request, "Hai rifiutato la delega.")
            # Crea notifica di risposta all'Admin qui...
            return redirect("dashboard")

        messages.warning(request, "Azione non permessa: la delega è già stata gestita o non sei il destinatario.")
        return redirect("notification_detail", pk=notification.pk)

    # 6. Render template
    return render(request, "notification_detail.html", {
        "notification": notification,
        "delegation": delegation,  # <--- QUESTA VARIABILE ORA CONTIENE L'OGGETTO
        "can_accept": can_accept,
        "can_reject": can_reject,
    })




@login_required
def accept_delegation(request, pk: int):
    """
    Il collaboratore accetta la delega.
    """
    delega = get_object_or_404(Delegation, pk=pk)

    # sicurezza: solo il proprietario può accettare
    if delega.collaborator != request.user:
        return redirect("dashboard")

    delega.accepted = True
    delega.save()

    messages.success(request, "Hai accettato la delega.")
    return redirect("dashboard")
