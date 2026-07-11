# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
import json

from .forms import (
    LoginForm, MeasurementForm, GoalForm,
    AddTraineeForm, AddTrainerForm, MessageForm,
    EditTraineeForm,
)
from .models import Measurement, Goal, Message, CustomUser

User = get_user_model()


# ---------- AUTH ----------
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ---------- HOME ----------
@login_required
def home_view(request):
    user = request.user
    if user.is_superuser:
        return redirect(reverse('admin:index'))
    elif user.role == 'trainer':
        trainees = user.trainees.all()
        helpers = user.helpers.all()
        return render(request, 'core/home_trainer.html', {
            'trainees': trainees,
            'helpers': helpers,
        })
    elif user.role == 'trainee':
        return render(request, 'core/home_trainee.html', {'user': user})
    return render(request, 'core/home.html', {'user': user})


# ---------- USERS ----------
@login_required
def user_list_view(request):
    user = request.user
    users = CustomUser.objects.none()

    if user.role == 'trainer':
        users = CustomUser.objects.filter(
            Q(head_trainer=user) | Q(main_trainer=user)
        ).distinct()
    elif user.role == 'trainee':
        users = user.get_assigned_trainers()
    return render(request, 'core/user_list.html', {'users': users})


@login_required
def add_trainee(request):
    if request.user.role != 'trainer':
        return HttpResponseForbidden("Nemáš oprávnenie.")

    if request.method == 'POST':
        form = AddTraineeForm(request.POST)
        if form.is_valid():
            trainee = form.save(commit=False)
            trainee.role = 'trainee'
            trainee.head_trainer = request.user
            pwd = form.cleaned_data.get('password')
            if pwd:
                trainee.set_password(pwd)
            trainee.save()
            messages.success(request, "Trainee pridaný úspešne.")
            return redirect('user_list')
    else:
        form = AddTraineeForm()
    return render(request, 'core/add_trainee.html', {'form': form})


@login_required
def add_trainer(request):
    if request.user.role != 'trainer':
        return HttpResponseForbidden("Nemáš oprávnenie.")

    if request.method == 'POST':
        form = AddTrainerForm(request.POST)
        if form.is_valid():
            trainer = form.save(commit=False)
            trainer.role = 'trainer'
            pwd = form.cleaned_data.get('password')
            if pwd:
                trainer.set_password(pwd)
            trainer.save()
            trainer.main_trainer.add(request.user)
            messages.success(request, "Pomocný tréner pridaný úspešne.")
            return redirect('user_list')
    else:
        form = AddTrainerForm()
    return render(request, 'core/add_trainer.html', {'form': form})


@login_required

def register_trainer_view(request):
    """Admin / superuser pridá trénera cez administratívnu registráciu (alternatíva k add_trainer)."""
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Nemáš oprávnenie.")
    if request.method == 'POST':
        form = AddTrainerForm(request.POST)
        if form.is_valid():
            trainer = form.save(commit=False)
            trainer.role = 'trainer'
            pwd = form.cleaned_data.get('password') if 'password' in form.cleaned_data else None
            if pwd:
                trainer.set_password(pwd)
            trainer.save()
            # admin nezapína main_trainer implicitne
            return redirect('user_list')
    else:
        form = AddTrainerForm()
    return render(request, 'core/register_trainer.html', {'form': form})


@login_required
def register_trainee_view(request):
    """Trainer pridá trainee (alias add_trainee) - dostupné ak chceš samostatnú cestu."""
    return add_trainee(request)


# ---------- MEASUREMENTS ----------
@login_required
def add_measurement(request):
    """Trainee pridá svoje meranie (vrátane foto)."""
    if request.user.role != 'trainee':
        return HttpResponseForbidden("Nemáš oprávnenie.")
    if request.method == 'POST':
        form = MeasurementForm(request.POST, request.FILES)
        if form.is_valid():
            measurement = form.save(commit=False)
            measurement.user = request.user
            measurement.save()
            return redirect('measurement_list')
    else:
        form = MeasurementForm()
    return render(request, 'core/add_measurement.html', {'form': form})


@login_required
def measurement_list(request):
    """
    Zoznam meraní:
    - tréner vidí merania svojich trainee
    - trainee vidí svoje
    Also handles preview requests (?preview=<id>) by returning a signed one-time URL.
    """
    user = request.user
    measurements = Measurement.objects.none()
    trainees = CustomUser.objects.none()
    selected_trainee = None

    if user.role == 'trainer':
        trainees = user.trainees.all().order_by('username')
        selected_trainee_id = request.GET.get('trainee')
        if selected_trainee_id:
            try:
                selected_trainee = trainees.get(id=selected_trainee_id)
                measurements = Measurement.objects.filter(user=selected_trainee).order_by('-date')
            except CustomUser.DoesNotExist:
                measurements = Measurement.objects.none()
        else:
            trainee_ids = trainees.values_list('id', flat=True)
            measurements = Measurement.objects.filter(user_id__in=trainee_ids).order_by('-date')

    elif user.role == 'trainee':
        measurements = Measurement.objects.filter(user=user).order_by('-date')

    return render(request, 'core/measurement_list.html', {
        'measurements': measurements,
        'trainees': trainees,
        'selected_trainee': selected_trainee,
    })


@login_required
def measurement_detail(request, pk):
    measurement = get_object_or_404(Measurement, pk=pk)
    user = request.user

    if user.role == 'trainee' and measurement.user != user:
        return HttpResponseForbidden("Nemáš prístup k tomuto meraniu.")

    if user.role == 'trainer' and measurement.user.head_trainer != user and measurement.user not in user.trainees.all():
        return HttpResponseForbidden("Nemáš prístup k tomuto meraniu.")

    return render(request, 'core/measurement_detail.html', {'measurement': measurement})


@login_required
def measurement_charts(request, user_id):
    """Vypočíta a pošle dáta pre Chart.js (ako JSON stringy v kontexte)."""
    other_user = get_object_or_404(User, pk=user_id)
    current_user = request.user

    # prístupové pravidlá:
    if current_user.role == 'trainee' and current_user != other_user:
        return HttpResponseForbidden("Nemáš oprávnenie zobraziť merania iného používateľa.")

    if current_user.role == 'trainer':
        # tréner môže vidieť hlavné tréningy alebo ak je pomocný tréner priradený
        allowed = False
        if other_user.head_trainer == current_user:
            allowed = True
        if hasattr(other_user, 'main_trainer') and current_user in other_user.main_trainer.all():
            allowed = True
        if other_user in current_user.trainees.all():
            allowed = True
        if not allowed:
            return HttpResponseForbidden("Nemáš oprávnenie zobraziť merania iného používateľa.")

    measurements = Measurement.objects.filter(user=other_user).order_by('date')

    dates = [m.date.strftime('%Y-%m-%d') for m in measurements]
    weights = [float(m.weight) if m.weight is not None else None for m in measurements]
    chests = [float(m.chest) if m.chest is not None else None for m in measurements]
    waists = [float(m.waist) if m.waist is not None else None for m in measurements]
    biceps = [float(m.biceps) if m.biceps is not None else None for m in measurements]
    thighs = [float(m.thigh) if m.thigh is not None else None for m in measurements]
    calfs = [float(m.calf) if m.calf is not None else None for m in measurements]

    context = {
        'other_user': other_user,
        # posielame JSON-stringy, v šablóne použijeme {{ weights|safe }} atď.
        'dates': json.dumps(dates),
        'weights': json.dumps(weights),
        'chests': json.dumps(chests),
        'waists': json.dumps(waists),
        'biceps': json.dumps(biceps),
        'thighs': json.dumps(thighs),
        'calfs': json.dumps(calfs),
    }
    return render(request, 'core/measurement_charts.html', context)


# ---------- GOALS ----------
@login_required
def goal_list(request):
    user = request.user
    if user.role == 'trainer':
        trainee_ids = user.trainees.all().values_list('id', flat=True)
        goals = Goal.objects.filter(user_id__in=trainee_ids).order_by('-target_date')
    else:
        goals = Goal.objects.filter(user=user).order_by('-target_date')
    return render(request, 'core/goal_list.html', {'goals': goals})


@login_required
def goal_add(request):
    if request.user.role != 'trainee':
        return HttpResponseForbidden("Nemáš oprávnenie.")
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('goal_list')
    else:
        form = GoalForm()
    return render(request, 'core/add_goal.html', {'form': form})


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    user = request.user
    if user.role == 'trainee' and goal.user != user:
        return HttpResponseForbidden("Nemáš prístup k tomuto cieľu.")
    if user.role == 'trainer' and goal.user.head_trainer != user and goal.user not in user.trainees.all():
        return HttpResponseForbidden("Nemáš prístup k tomuto cieľu.")
    return render(request, 'core/goal_detail.html', {'goal': goal})


@login_required
def goal_toggle_complete(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    user = request.user
    if user.role == 'trainee' and goal.user != user:
        return HttpResponseForbidden("Nemáš prístup k tomuto cieľu.")
    if user.role == 'trainer' and goal.user.head_trainer != user and goal.user not in user.trainees.all():
        return HttpResponseForbidden("Nemáš prístup k tomuto cieľu.")
    if request.method == 'POST':
        goal.is_completed = not goal.is_completed
        goal.save()
    return redirect('goal_list')


# ---------- MESSAGES (CHAT) ----------
@login_required
def chat_view(request, user_id):
    """
    Zobrazí chat medzi prihláseným userom a other_user.
    Podporuje AJAX refresh: ak request má X-Requested-With: XMLHttpRequest, vráti partial _messages.html.
    """
    current_user = request.user
    other_user = get_object_or_404(CustomUser, pk=user_id)

    # Kontrola práv:
    allowed = False
    # trainer môže komunikovať so svojimi trainee (hlavnými) alebo s trainee, kde je priradený ako pomocny (main_trainer)
    if current_user.role == 'trainer':
        if other_user.role == 'trainee':
            if other_user.head_trainer == current_user:
                allowed = True
            # ak existuje reverse M2M 'main_trainer' (trainee.main_trainer) -> skontrolujeme
            if hasattr(other_user, 'main_trainer') and current_user in other_user.main_trainer.all():
                allowed = True
        # trainer <-> helper_trainer (trener môže komunikovať aj so svojimi helpers)
        if other_user.role == 'trainer' and other_user in current_user.helpers.all():
            allowed = True

    # trainee môže komunikovať len s assigned trainers (head_trainer a ďalší priradení)
    if current_user.role == 'trainee':
        try:
            assigned = request.user.get_assigned_trainers()
            if other_user in assigned:
                allowed = True
        except Exception:
            # fallback: skontroluj head_trainer a main_trainer reverse
            if other_user == current_user.head_trainer:
                allowed = True
            if hasattr(current_user, 'main_trainer') and other_user in current_user.main_trainer.all():
                allowed = True

    if not allowed:
        return HttpResponseForbidden("Nemáš oprávnenie poslať správu tomuto používateľovi.")

    # Načítanie správ
    messages_qs = Message.objects.filter(
        Q(sender=current_user, receiver=other_user) |
        Q(sender=other_user, receiver=current_user)
    ).order_by('timestamp')

    # Označiť prípadné nové správy ako prečítané (len tie, ktoré sú určené current_user)
    messages_qs.filter(receiver=current_user, is_read=False).update(is_read=True)

    # POST - odoslanie správy
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = current_user
            msg.receiver = other_user
            msg.save()
            # po uložení načítame znovu správy (vrátane práve prijatej)
            messages_qs = Message.objects.filter(
                Q(sender=current_user, receiver=other_user) |
                Q(sender=other_user, receiver=current_user)
            ).order_by('timestamp')
            # ak AJAX (fetch), vraciame iba partial HTML
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return render(request, 'core/_messages.html', {
                    'messages': messages_qs,
                    'request': request
                })
            return redirect('chat', user_id=other_user.id)
    else:
        form = MessageForm()

    # AJAX refresh správ (vrátime partial)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/_messages.html', {
            'messages': messages_qs,
            'request': request
        })

    # Plné zobrazenie stránky
    return render(request, 'core/chat.html', {
        'other_user': other_user,
        'messages': messages_qs,
        'form': form
    })


@login_required

def edit_trainee(request, user_id):
    if request.user.role != 'trainer':
        return HttpResponseForbidden("Nemáš oprávnenie.")

    trainee = get_object_or_404(CustomUser, id=user_id, role='trainee')
    if trainee.head_trainer != request.user:
        return HttpResponseForbidden("Nemáš oprávnenie upravovať tohto zverenca.")

    if request.method == 'POST':
        form = EditTraineeForm(request.POST, instance=trainee)
        if form.is_valid():
            form.save()
            messages.success(request, "Zverenec bol upravený.")
            return redirect('user_list')
    else:
        form = EditTraineeForm(instance=trainee)

    return render(request, 'core/edit_trainee.html', {'form': form, 'trainee': trainee})


@login_required
def delete_trainee(request, user_id):
    if request.user.role != 'trainer':
        return HttpResponseForbidden("Nemáš oprávnenie.")

    trainee = get_object_or_404(CustomUser, id=user_id, role='trainee')
    if trainee.head_trainer != request.user:
        return HttpResponseForbidden("Nemáš oprávnenie zmazať tohto zverenca.")

    if request.method == 'POST':
        trainee.delete()
        messages.success(request, "Zverenec bol vymazaný.")
        return redirect('user_list')

    return render(request, 'core/delete_trainee.html', {'trainee': trainee})


# ---------- MEASUREMENTS ----------
@login_required
def add_measurement(request):
    if request.user.role != 'trainee':
        return HttpResponseForbidden("Nemáš oprávnenie.")

    if request.method == 'POST':
        form = MeasurementForm(request.POST, request.FILES)
        if form.is_valid():
            measurement = form.save(commit=False)
            measurement.user = request.user
            measurement.save()
            messages.success(request, "Meranie pridané.")
            return redirect('measurement_list')
    else:
        form = MeasurementForm()
    return render(request, 'core/add_measurement.html', {'form': form})


@login_required
def measurement_list(request):
    user = request.user
    measurements = Measurement.objects.none()
    trainees = CustomUser.objects.none()
    selected_trainee = None

    if user.role == 'trainer':
        trainees = user.trainees.all()
        selected_id = request.GET.get('trainee')
        if selected_id:
            selected_trainee = trainees.filter(id=selected_id).first()
            if selected_trainee:
                measurements = Measurement.objects.filter(user=selected_trainee)
        else:
            measurements = Measurement.objects.filter(user__in=trainees)
    elif user.role == 'trainee':
        measurements = Measurement.objects.filter(user=user)

    return render(request, 'core/measurement_list.html', {
        'measurements': measurements.order_by('-date'),
        'trainees': trainees,
        'selected_trainee': selected_trainee,
    })


@login_required
def measurement_detail(request, pk):
    measurement = get_object_or_404(Measurement, pk=pk)
    user = request.user
    if user.role == 'trainee' and measurement.user != user:
        return HttpResponseForbidden("Nemáš prístup k tomuto meraniu.")
    if user.role == 'trainer' and measurement.user.head_trainer != user:
        return HttpResponseForbidden("Nemáš prístup k tomuto meraniu.")
    return render(request, 'core/measurement_detail.html', {'measurement': measurement})


@login_required
def measurement_charts(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    current_user = request.user

    if current_user.role == 'trainee' and current_user != other_user:
        return HttpResponseForbidden("Nemáš oprávnenie.")

    if current_user.role == 'trainer' and other_user.head_trainer != current_user and current_user not in other_user.main_trainer.all():
        return HttpResponseForbidden("Nemáš oprávnenie.")

    measurements = Measurement.objects.filter(user=other_user).order_by('date')
    context = {
        'other_user': other_user,
        'dates': json.dumps([m.date.strftime('%Y-%m-%d') for m in measurements]),
        'weights': json.dumps([float(m.weight) if m.weight else None for m in measurements]),
        'chests': json.dumps([float(m.chest) if m.chest else None for m in measurements]),
        'waists': json.dumps([float(m.waist) if m.waist else None for m in measurements]),
        'biceps': json.dumps([float(m.biceps) if m.biceps else None for m in measurements]),
        'thighs': json.dumps([float(m.thigh) if m.thigh else None for m in measurements]),
        'calfs': json.dumps([float(m.calf) if m.calf else None for m in measurements]),
    }
    return render(request, 'core/measurement_charts.html', context)


# ---------- GOALS ----------
@login_required
def goal_list(request):
    user = request.user
    if user.role == 'trainer':
        goals = Goal.objects.filter(user__in=user.trainees.all())
    else:
        goals = Goal.objects.filter(user=user)
    return render(request, 'core/goal_list.html', {'goals': goals})


@login_required
def goal_add(request):
    if request.user.role != 'trainee':
        return HttpResponseForbidden("Nemáš oprávnenie.")
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, "Cieľ pridaný.")
            return redirect('goal_list')
    else:
        form = GoalForm()
    return render(request, 'core/add_goal.html', {'form': form})


@login_required
def goal_toggle_complete(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    user = request.user
    if user.role == 'trainee' and goal.user != user:
        return HttpResponseForbidden("Nemáš prístup.")
    if user.role == 'trainer' and goal.user.head_trainer != user:
        return HttpResponseForbidden("Nemáš prístup.")
    if request.method == 'POST':
        goal.is_completed = not goal.is_completed
        goal.save()
    return redirect('goal_list')


# ---------- CHAT ----------
@login_required
def chat_view(request, user_id):
    current_user = request.user
    other_user = get_object_or_404(CustomUser, pk=user_id)
    allowed = False

    if current_user.role == 'trainer':
        if other_user.role == 'trainee':
            if other_user.head_trainer == current_user or current_user in other_user.main_trainer.all():
                allowed = True
        elif other_user.role == 'trainer' and (other_user in current_user.helpers.all() or current_user in other_user.helpers.all()):
            allowed = True
    elif current_user.role == 'trainee':
        if other_user in current_user.get_assigned_trainers():
            allowed = True

    if not allowed:
        return HttpResponseForbidden("Nemáš oprávnenie poslať správu tomuto používateľovi.")

    messages_qs = Message.objects.filter(
        Q(sender=current_user, receiver=other_user) |
        Q(sender=other_user, receiver=current_user)
    ).order_by('timestamp')

    messages_qs.filter(receiver=current_user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = current_user
            msg.receiver = other_user
            msg.save()
            messages_qs = Message.objects.filter(
                Q(sender=current_user, receiver=other_user) |
                Q(sender=other_user, receiver=current_user)
            ).order_by('timestamp')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return render(request, 'core/_messages.html', {'messages': messages_qs})
            return redirect('chat', user_id=other_user.id)
    else:
        form = MessageForm()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'core/_messages.html', {'messages': messages_qs})

    return render(request, 'core/chat.html', {'other_user': other_user, 'messages': messages_qs, 'form': form})


# ---------- COMPARE PHOTOS ----------
@login_required
def compare_photos(request, user_id):
    trainee = get_object_or_404(CustomUser, pk=user_id)
    if request.user.role != 'trainer':
        return HttpResponseForbidden("Nemáš oprávnenie.")
    if trainee.head_trainer != request.user and trainee not in request.user.trainees.all():
        return HttpResponseForbidden("Nemáš oprávnenie k fotkám tohto používateľa.")

    measurements = Measurement.objects.filter(user=trainee, photo__isnull=False).exclude(photo='').order_by('-date')
    selected_ids = request.GET.getlist('photos')
    selected_measurements = measurements.filter(id__in=selected_ids)

    return render(request, 'core/compare_photos.html', {
        'trainee': trainee,
        'measurements': measurements,
        'selected_measurements': selected_measurements,
        'selected_ids': selected_ids,
    })
