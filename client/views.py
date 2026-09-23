from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import JsonResponse

from apps.models import Product, Order, Payment, Category
from .forms import OrderRequestForm, OrderRequestItemFormSet, ClienteForm
from apps import telegram_bot
from .models import OrderRequest, Cliente

from apps.decorators import client_required, admin_required


def _get_cliente(request):
    return getattr(request.user, 'cliente_profile', None)


@client_required
def client_dashboard(request):
    cliente = _get_cliente(request)
    if not cliente:
        messages.error(request, "Sizning hisobingizga mijoz profili biriktirilmagan. Admin bilan bog'laning.")
        return redirect('login')

    orders = cliente.orders.exclude(status='cancelled')
    total_sales = orders.aggregate(s=Sum('total_sum'))['s'] or 0
    total_paid = Payment.objects.filter(order__in=orders, confirmed=True).aggregate(s=Sum('amount'))['s'] or 0
    debt = total_sales - total_paid

    context = {
        'cliente': cliente,
        'debt': debt,
        'total_sales': total_sales,
        'total_paid': total_paid,
        'recent_requests': cliente.order_requests.all()[:5],
        'recent_orders': orders.order_by('-date_created')[:5],
    }
    return render(request, 'clients/dashboard.html', context)


@client_required
def client_product_list(request):
    q = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')

    products = Product.objects.filter(is_active=True).select_related('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))

    categories = Category.objects.filter(is_active=True)
    current_category = categories.filter(slug=category_slug).first() if category_slug else None

    return render(request, 'clients/product_list.html', {
        'products': products, 'q': q,
        'categories': categories, 'current_category': current_category, 'category_slug': category_slug,
    })


@client_required
def client_payment_list(request):
    cliente = _get_cliente(request)
    orders = cliente.orders.exclude(status='cancelled')
    payments = Payment.objects.filter(order__in=orders).select_related('order').order_by('-date_created')
    return render(request, 'clients/payment_list.html', {'orders': orders, 'payments': payments})


@client_required
def client_order_request_list(request):
    cliente = _get_cliente(request)
    reqs = cliente.order_requests.prefetch_related('items__product')
    return render(request, 'clients/order_request_list.html', {'requests': reqs})


@client_required
def client_order_request_detail(request, pk):
    cliente = _get_cliente(request)
    req = get_object_or_404(
        OrderRequest.objects.prefetch_related('items__product'), pk=pk, cliente=cliente
    )
    return render(request, 'clients/order_request_detail.html', {'req': req})


@client_required
def client_order_request_create(request):
    cliente = _get_cliente(request)
    if request.method == 'POST':
        form = OrderRequestForm(request.POST)
        formset = OrderRequestItemFormSet(request.POST, prefix='items')
        if form.is_valid() and formset.is_valid():
            real_items = [
                f for f in formset
                if not f.cleaned_data.get('DELETE') and f.cleaned_data.get('product')
            ]
            if not real_items:
                messages.error(request, "Kamida bitta tovar tanlang.")
            else:
                req = form.save(commit=False)
                req.cliente = cliente
                req.save()
                for item_form in real_items:
                    item = item_form.save(commit=False)
                    item.request = req
                    item.save()

                telegram_bot.send_telegram_message(
                    f"🛒 <b>Yangi buyurtma so'rovi</b>\n\n"
                    f"<b>Mijoz:</b> {cliente}\n"
                    f"<b>Tovarlar soni:</b> {len(real_items)}\n"
                    f"<b>Jami:</b> {req.total_sum:,.0f} so'm"
                )
                messages.success(request, "So'rovingiz yuborildi. Admin tasdiqlashini kuting.")
                return redirect('client_order_request_detail', pk=req.pk)
    else:
        form = OrderRequestForm()
        formset = OrderRequestItemFormSet(prefix='items')

    return render(request, 'clients/order_request_form.html', {'form': form, 'formset': formset})


@client_required
def client_get_product_price(request):
    product_id = request.GET.get('product_id')
    try:
        product = Product.objects.get(pk=product_id, is_active=True)
        return JsonResponse({'price': product.price, 'stock': product.stock})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Tovar topilmadi'}, status=404)


# ════════════════════════════════════════════════
# CLIENTE (Mijoz)
# ════════════════════════════════════════════════

@admin_required
def cliente_list(request):
    q = request.GET.get('q', '')
    clientes = Cliente.objects.filter(is_active=True).select_related('agent')
    if q:
        clientes = clientes.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(firma_name__icontains=q) |
            Q(alternative_name__icontains=q) |
            Q(phone__icontains=q)
        )
    paginator = Paginator(clientes, 30)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {'clientes': page_obj, 'page_obj': page_obj, "q": q}
    return render(request, 'clients/list.html', context)


@admin_required
def cliente_detail(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    orders = cliente.orders.all()[:20]
    total_debt = (
            cliente.orders.filter(status='debt')
            .aggregate(s=Sum('total_sum'))['s'] or 0
    )
    context = {'cliente': cliente, 'orders': orders, 'total_debt': total_debt}
    return render(request, 'clients/detail.html', context)


@admin_required
def cliente_create(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Mijoz qo'shildi.")
            return redirect('cliente_list')
    else:
        form = ClienteForm()
    return render(request, 'clients/form.html', {'form': form, 'title': "Yangi mijoz"})


@admin_required
def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, "Mijoz yangilandi.")
            return redirect('cliente_detail', pk=pk)
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'clients/form.html', {'form': form, 'title': "Mijozni tahrirlash"})


@admin_required
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.is_active = False
        cliente.save()
        messages.success(request, "Mijoz o'chirildi.")
        return redirect('cliente_list')
    return render(request, 'confirm_delete.html', {'object': cliente, 'type': 'Mijoz'})


@client_required
def client_order_detail(request, pk):
    """
    Mijoz o'ziga tegishli nakladnoyning to'liq tafsilotini ko'radi:
    yaratilgan sana, nakladnoy rasmi, olingan tovarlar, to'langan/qolgan qarz.
    """
    cliente = get_object_or_404(Cliente, user=request.user)
    order = get_object_or_404(
        Order.objects.select_related('cliente', 'agent').prefetch_related('items__product'),
        pk=pk, cliente=cliente
    )
    payments = order.payments.all()
    total_paid = payments.filter(confirmed=True).aggregate(s=Sum('amount'))['s'] or 0
    remaining_debt = order.total_sum - total_paid

    context = {
        'order': order,
        'payments': payments,
        'total_paid': total_paid,
        'remaining_debt': remaining_debt,
    }
    return render(request, 'clients/order_detail.html', context)
