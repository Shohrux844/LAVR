"""
agent/views.py — to'liq tuzatilgan versiya

O'zgarishlar (shu tahrirda qilingan):
  - @agent_required BARCHA agent-panel funksiyalariga QAYTA YOQILDI
    (avval commentga olib qo'yilgan edi — bu istalgan foydalanuvchi,
    hatto login qilmagan odam ham, agent panelga kirishi mumkinligini
    anglatardi — jiddiy xavfsizlik zaifligi edi).
  - Yangi agent_balance_calculate_ajax funksiyasi qo'shildi — "Ostatka
    kiritish" formasida "Avtomatik hisoblash" tugmasi shu yerga murojaat qiladi.
  - Ishlatilmagan importlar (functools.wraps) olib tashlandi.
"""
import math
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date

# agent app o'z modellari
from agent.models import Agent, AgentBalance
from agent.forms import AgentForm, AgentBalanceForm
from agent.services import calculate_daily_cash_collected

# apps dan keraklilar
from apps.models import (
    Order, Payment, Product,
    Visit, PointOfInterest, Salary,
)
from apps import telegram_bot
from client.forms import ClienteForm
from client.models import Cliente

from apps.decorators import agent_required, admin_required


def get_agent(request):
    return getattr(request.user, 'agent_profile', None)


# ════════════════════════════════════════════════
# ADMIN — AGENTLAR BOSHQARUVI (is_staff uchun)
# ════════════════════════════════════════════════

@admin_required
def agent_list(request):
    agents = Agent.objects.filter(is_active=True).annotate(
        order_count=Count('orders'),
        total_sales=Sum('orders__total_sum'),
    )
    return render(request, 'agents/list.html', {'agents': agents})


@admin_required
def agent_detail(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    orders = agent.orders.all()[:20]
    balances = agent.balances.all()[:10]
    salaries = agent.salaries.all()[:6]
    today_balance = agent.balances.filter(date=date.today()).first()
    return render(request, 'agents/detail.html', {
        'agent': agent,
        'orders': orders,
        'balances': balances,
        'salaries': salaries,
        'today_balance': today_balance,
    })


@admin_required
def agent_create(request):
    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Agent qo'shildi.")
            return redirect('agent_list')
    else:
        form = AgentForm()
    return render(request, 'agents/form.html', {'form': form, 'title': "Yangi agent"})


@admin_required
def agent_update(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    if request.method == 'POST':
        form = AgentForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            messages.success(request, "Agent yangilandi.")
            return redirect('agent_detail', pk=pk)
    else:
        form = AgentForm(instance=agent)
    return render(request, 'agents/form.html', {'form': form, 'title': "Agentni tahrirlash"})


@admin_required
def agent_delete(request, pk):
    agent = get_object_or_404(Agent, pk=pk)
    if request.method == 'POST':
        agent.is_active = False
        agent.save()
        messages.success(request, "Agent o'chirildi.")
        return redirect('agent_list')
    return render(request, 'confirm_delete.html', {'object': agent, 'type': 'Agent'})


# ════════════════════════════════════════════════
# ADMIN — AGENT BALANS (Ostatka)
# ════════════════════════════════════════════════

@admin_required
def agent_balance_list(request):
    today = date.today()
    balances = AgentBalance.objects.filter(date=today).select_related('agent').order_by('-given_amount')
    return render(request, 'balances/list.html', {'balances': balances, 'today': today})


@admin_required
def agent_balance_create(request):
    if request.method == 'POST':
        form = AgentBalanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ostatka kiritildi.")
            return redirect('agent_balance_list')
    else:
        form = AgentBalanceForm()
    return render(request, 'balances/form.html', {'form': form, 'title': "Ostatka kiritish"})


@admin_required
def agent_balance_update(request, pk):
    balance = get_object_or_404(AgentBalance, pk=pk)
    if request.method == 'POST':
        form = AgentBalanceForm(request.POST, instance=balance)
        if form.is_valid():
            form.save()
            messages.success(request, "Ostatka yangilandi.")
            return redirect('agent_balance_list')
    else:
        form = AgentBalanceForm(instance=balance)
    return render(request, 'balances/form.html', {'form': form, 'title': "Ostatkani tahrirlash"})


@admin_required
def agent_balance_calculate_ajax(request):
    """
    "Ostatka kiritish" formasida "Avtomatik hisoblash" tugmasi bosilganda
    chaqiriladi — tanlangan agent va sana uchun o'sha kuni yig'ilgan
    tasdiqlangan naqd to'lovlar summasini hisoblab, JSON qaytaradi.
    """
    agent_id = request.GET.get('agent_id')
    date_str = request.GET.get('date')

    if not agent_id:
        return JsonResponse({'error': 'agent_id kerak'}, status=400)

    agent = get_object_or_404(Agent, pk=agent_id)
    target_date = parse_date(date_str) if date_str else None
    if not target_date:
        target_date = date.today()

    amount = calculate_daily_cash_collected(agent, target_date)
    return JsonResponse({'given_amount': amount})


# ════════════════════════════════════════════════
# AGENT PANEL — DASHBOARD
# ════════════════════════════════════════════════

@agent_required
def agent_dashboard(request):
    agent = get_agent(request)
    today = date.today()

    week_start = today - timedelta(days=today.weekday())
    week_orders = Order.objects.filter(
        agent=agent,
        date_created__date__gte=week_start,
        date_created__date__lte=today,
    ).exclude(status='cancelled')
    week_sales = week_orders.aggregate(s=Sum('total_sum'))['s'] or 0
    week_commission = int(week_sales * float(agent.commission_rate) / 100)

    month_start = today.replace(day=1)
    month_orders = Order.objects.filter(
        agent=agent,
        date_created__date__gte=month_start,
        date_created__date__lte=today,
    ).exclude(status='cancelled')
    month_sales = month_orders.aggregate(s=Sum('total_sum'))['s'] or 0
    month_commission = int(month_sales * float(agent.commission_rate) / 100)

    # Mijozlar qarz holati
    cliente_debts = []
    for c in Cliente.objects.filter(agent=agent, is_active=True):
        orders = Order.objects.filter(cliente=c).exclude(status='cancelled')
        total = orders.aggregate(s=Sum('total_sum'))['s'] or 0
        total_paid = Payment.objects.filter(order__in=orders, confirmed=True).aggregate(s=Sum('amount'))['s'] or 0
        cliente_debts.append({'cliente': c, 'total_sales': total, 'total_paid': total_paid, 'debt': total - total_paid})
    cliente_debts.sort(key=lambda x: x['debt'], reverse=True)

    today_balance = AgentBalance.objects.filter(agent=agent, date=today).first()
    recent_orders = Order.objects.filter(agent=agent).select_related('cliente').order_by('-date_created')[:8]
    salaries = Salary.objects.filter(agent=agent).order_by('-month')[:3]

    return render(request, 'agents/agent_dashboard.html', {
        'agent': agent, 'today': today,
        'week_sales': week_sales, 'week_commission': week_commission,
        'week_orders_count': week_orders.count(),
        'month_sales': month_sales, 'month_commission': month_commission,
        'month_orders_count': month_orders.count(),
        'cliente_debts': cliente_debts,
        'today_balance': today_balance,
        'recent_orders': recent_orders,
        'salaries': salaries,
    })


# ════════════════════════════════════════════════
# AGENT PANEL — NAKLADNOYLAR
# ════════════════════════════════════════════════

@agent_required
def agent_order_list(request):
    agent = get_agent(request)
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    orders = Order.objects.filter(agent=agent).select_related('cliente')
    if q:
        orders = orders.filter(
            Q(number__icontains=q) |
            Q(cliente__first_name__icontains=q) |
            Q(cliente__firma_name__icontains=q) |
            Q(cliente__alternative_name__icontains=q)
        )
    if status_filter:
        orders = orders.filter(status=status_filter)
    if date_from:
        orders = orders.filter(date_created__date__gte=date_from)
    if date_to:
        orders = orders.filter(date_created__date__lte=date_to)
    orders = orders.order_by('-date_created')

    return render(request, 'agents/order_list.html', {
        'orders': orders, 'q': q,
        'status_filter': status_filter,
        'date_from': date_from, 'date_to': date_to,
        'status_choices': Order.Status.choices,
    })


@agent_required
def agent_order_detail(request, pk):
    agent = get_agent(request)
    order = get_object_or_404(
        Order.objects.select_related('cliente').prefetch_related('items__product'),
        pk=pk, agent=agent,
    )
    payments = order.payments.all()
    total_paid = payments.filter(confirmed=True).aggregate(s=Sum('amount'))['s'] or 0
    return render(request, 'agents/order_detail.html', {
        'order': order, 'payments': payments,
        'total_paid': total_paid,
        'remaining_debt': order.total_sum - total_paid,
    })


# ════════════════════════════════════════════════
# AGENT PANEL — TOVARLAR
# ════════════════════════════════════════════════

@agent_required
def agent_product_list(request):
    q = request.GET.get('q', '')
    products = Product.objects.filter(is_active=True)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    return render(request, 'agents/product_list.html', {
        'products': products.order_by('name'), 'q': q,
    })


@agent_required
def agent_product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return render(request, 'agents/product_detail.html', {'product': product})


# ════════════════════════════════════════════════
# AGENT PANEL — MIJOZLAR
# ════════════════════════════════════════════════

@agent_required
def agent_cliente_list(request):
    agent = get_agent(request)
    q = request.GET.get('q', '')
    clientes = Cliente.objects.filter(agent=agent, is_active=True)
    if q:
        clientes = clientes.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) |
            Q(firma_name__icontains=q) | Q(alternative_name__icontains=q) |
            Q(phone__icontains=q)
        )
    return render(request, 'agents/cliente_list.html', {'clients': clientes, 'q': q})


@agent_required
def agent_cliente_create(request):
    agent = get_agent(request)
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.agent = agent
            cliente.save()
            messages.success(request, f"{cliente} qo'shildi.")
            return redirect('agent_cliente_list')
    else:
        form = ClienteForm(initial={'agent': agent})
        form.fields['agent'].widget.attrs['disabled'] = True
    return render(request, 'agents/cliente_form.html', {'form': form, 'title': "Yangi mijoz"})


# ════════════════════════════════════════════════
# AGENT PANEL — MAOSH
# ════════════════════════════════════════════════

@agent_required
def agent_salary_list(request):
    agent = get_agent(request)
    salaries = Salary.objects.filter(agent=agent).order_by('-month')
    return render(request, 'agents/salary_list.html', {'agent': agent, 'salaries': salaries})


# ════════════════════════════════════════════════
# AGENT PANEL — GPS KUZATUV
# ════════════════════════════════════════════════

AGENT_PROXIMITY_METERS = 500
AGENT_NOTIFY_COOLDOWN_MINUTES = 30


def _haversine(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@agent_required
def agent_road_tracking(request):
    agent = get_agent(request)
    return render(request, 'agents/road_tracking.html', {
        'agent': agent,
        'proximity_radius': AGENT_PROXIMITY_METERS,
    })


@agent_required
def agent_check_nearby(request):
    agent = get_agent(request)
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'error': "Koordinata noto'g'ri"}, status=400)

    cooldown_cutoff = timezone.now() - timedelta(minutes=AGENT_NOTIFY_COOLDOWN_MINUTES)

    # ── AZS / Avto-do'konlar ─────────────────────────────
    nearby_points = []
    for p in PointOfInterest.objects.filter(is_active=True).select_related('cliente'):
        dist = _haversine(lat, lng, p.latitude, p.longitude)
        if dist > AGENT_PROXIMITY_METERS:
            continue

        debt = 0
        if p.has_contract:
            p_orders = Order.objects.filter(cliente=p.cliente).exclude(status='cancelled')
            paid = Payment.objects.filter(order__in=p_orders, confirmed=True).aggregate(s=Sum('amount'))['s'] or 0
            debt = (p_orders.aggregate(s=Sum('total_sum'))['s'] or 0) - paid

        just_notified = False
        if not Visit.objects.filter(agent=agent, point=p, date_created__gte=cooldown_cutoff).exists():
            visit = Visit.objects.create(agent=agent, point=p, latitude=lat, longitude=lng)
            # ─── BACKGROUND yuborish ───
            # agent_check_nearby JS tomonidan HAR 15 SONIYADA chaqiriladi
            # (road_tracking.html dagi CHECK_INTERVAL) — shuning uchun bu
            # yerda Telegram javobini KUTISH mumkin emas, aks holda agentning
            # GPS-kuzatuv sahifasi sekinlashib qoladi. run_async() orqali
            # xabar orqa fonda yuboriladi, javob darhol qaytadi.
            if p.has_contract:
                telegram_bot.notify_visit_report_async(visit, debt_amount=debt)
            else:
                telegram_bot.notify_new_point_async(visit)
            just_notified = True

        nearby_points.append({
            'id': p.pk, 'name': p.name, 'kind': p.get_kind_display(),
            'distance': round(dist), 'has_contract': p.has_contract,
            'cliente': str(p.cliente) if p.cliente else None,
            'debt': debt, 'just_notified': just_notified,
        })

    # ── Agentga biriktirilgan mijozlar ───────────────────
    nearby_clientes = []
    for c in Cliente.objects.filter(agent=agent, is_active=True).prefetch_related('points_of_interest'):
        poi = c.points_of_interest.filter(is_active=True).first()
        if not poi:
            continue
        dist = _haversine(lat, lng, poi.latitude, poi.longitude)
        if dist > AGENT_PROXIMITY_METERS:
            continue

        c_orders = Order.objects.filter(cliente=c).exclude(status='cancelled')
        total = c_orders.aggregate(s=Sum('total_sum'))['s'] or 0
        total_paid = Payment.objects.filter(order__in=c_orders, confirmed=True).aggregate(s=Sum('amount'))['s'] or 0

        nearby_clientes.append({
            'id': c.pk, 'name': str(c),
            'firma': c.firma_name or '',
            'alternative': c.alternative_name or '',
            'phone': c.phone or '',
            'distance': round(dist),
            'total_sales': total, 'total_paid': total_paid,
            'debt': total - total_paid,
        })

    nearby_points.sort(key=lambda x: x['distance'])
    nearby_clientes.sort(key=lambda x: x['distance'])

    return JsonResponse({'nearby_points': nearby_points, 'nearby_clientes': nearby_clientes})
