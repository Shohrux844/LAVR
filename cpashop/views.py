
import datetime

from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db.models import Q, Count, F, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, FormView, ListView, DetailView, UpdateView

from .auth import cpa_login, cpa_logout, get_cpa_user, authenticate_cpa_user
from .forms import AuthForm, ProfileForm, ChangePasswordForm, OrderForm, ThreadForm, OrderModelForm, PaymentModelForm
from .models import (
    CpaUser, Region, District, Category, Product, Wishlist, AdminSetting,
    Order, Thread,
)


class CpaLoginRequiredMixin:
    """django.contrib.auth.mixins.LoginRequiredMixin ning session-asosli muqobili."""
    cpa_login_url = reverse_lazy('cpashop:auth')

    def dispatch(self, request, *args, **kwargs):
        if not get_cpa_user(request):
            return redirect(self.cpa_login_url)
        return super().dispatch(request, *args, **kwargs)


# ════════════════════════════════════════════════
# AUTH (original: views/auth.py)
# ════════════════════════════════════════════════

def district_list_view(request):
    region_id = request.GET.get('region_id')
    districts = District.objects.filter(region_id=region_id).values('id', 'name')
    return JsonResponse(list(districts), safe=False)


class CustomLogoutView(View):
    def get(self, request):
        cpa_logout(request)
        return redirect('cpashop:home')


class ProfileFormView(CpaLoginRequiredMixin, FormView):
    form_class = ProfileForm
    template_name = 'cpashop/auth/profile.html'
    success_url = reverse_lazy('cpashop:profile')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        return data

    def form_valid(self, form):
        form.update(get_cpa_user(self.request))
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class AuthFormView(FormView):
    """Bitta forma — telefon bazada bor bo'lsa login, bo'lmasa ro'yxatdan o'tkazib login."""
    form_class = AuthForm
    template_name = 'cpashop/auth/auth.html'
    success_url = reverse_lazy('cpashop:home')

    def form_valid(self, form):
        phone_number = form.cleaned_data.get('phone_number')
        password = form.data.get('password')
        existing = CpaUser.objects.filter(phone_number=phone_number).first()
        if existing:
            user = authenticate_cpa_user(phone_number, password)
            if user:
                cpa_login(self.request, user)
            else:
                messages.error(self.request, 'Parol xato.')
                return redirect('cpashop:auth')
        else:
            user = form.create_user()
            cpa_login(self.request, user)
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class ChangePasswordFormView(CpaLoginRequiredMixin, FormView):
    form_class = ChangePasswordForm
    template_name = 'cpashop/auth/auth.html'
    success_url = reverse_lazy('cpashop:profile')

    def form_valid(self, form):
        cpa_user = get_cpa_user(self.request)
        old_password = form.data.get('old')
        if not check_password(old_password, cpa_user.password):
            messages.error(self.request, 'Parol xato.')
        else:
            form.update(cpa_user)
        return redirect('cpashop:profile')


# ════════════════════════════════════════════════
# HOME / KATALOG (original: views/home.py)
# ════════════════════════════════════════════════

class HomeListView(ListView):
    queryset = Category.objects.all()
    template_name = 'cpashop/home.html'
    context_object_name = "categories"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['products'] = Product.objects.all()
        cpa_user = get_cpa_user(self.request)
        if cpa_user:
            data['liked_products_id'] = Wishlist.objects.filter(user=cpa_user).values_list("product_id", flat=True)
        return data


class ProductListView(ListView):
    queryset = Product.objects.all()
    template_name = 'cpashop/menus/product-list.html'
    context_object_name = "products"

    def get_context_data(self, *, object_list=None, **kwargs):
        slug = self.kwargs.get('slug')
        category = Category.objects.filter(slug=slug).first()
        data = super().get_context_data(object_list=object_list, **kwargs)
        products = Product.objects.all()
        if slug != 'all':
            products = products.filter(category=category)
        query = self.request.GET.get('query')
        if query:
            products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
        data['products'] = products
        data['categories'] = Category.objects.all()
        cpa_user = get_cpa_user(self.request)
        if cpa_user:
            data['liked_products_id'] = Wishlist.objects.filter(user=cpa_user).values_list("product_id", flat=True)
        data['session_category'] = category
        return data


class WishlistView(CpaLoginRequiredMixin, View):
    def get(self, request, pk):
        cpa_user = get_cpa_user(request)
        liked = True
        like = Wishlist.objects.filter(product_id=pk, user=cpa_user)
        if like.exists():
            like.delete()
            liked = False
        else:
            Wishlist.objects.create(product_id=pk, user=cpa_user)
        return JsonResponse({"liked": liked})


class ProductSellListView(ListView):
    queryset = Product.objects.all()
    template_name = "cpashop/thread/market-list.html"
    context_object_name = "products"

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        products = data['products']
        slug = self.request.GET.get('category')
        if slug == 'top':
            products = Product.objects.annotate(order_count=Count(F('orders'))).order_by('order_count')[:10]
        elif slug and slug != "all":
            products = Product.objects.filter(category__slug=slug)
        data['products'] = products
        data['categories'] = Category.objects.all()
        return data


class LikeListView(CpaLoginRequiredMixin, ListView):
    queryset = Wishlist.objects.all()
    template_name = 'cpashop/menus/wish-list.html'
    context_object_name = 'products'

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        cpa_user = get_cpa_user(self.request)
        data['products'] = Product.objects.filter(wishlist__user=cpa_user)
        data['liked_products_id'] = Wishlist.objects.filter(user=cpa_user).values_list("product_id", flat=True)
        return data


class CompetitionListView(ListView):
    queryset = CpaUser.objects.all()
    template_name = 'cpashop/menus/competition.html'
    context_object_name = "users"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['site'] = AdminSetting.objects.first()
        return data

    def get_queryset(self):
        query = super().get_queryset()
        query = query.annotate(
            order_count=Count('thread__orders', filter=Q(thread__orders__status=Order.StatusType.COMPLETED))
        ).order_by("-order_count").only('first_name')
        return query


class ArchivedTemplateView(CpaLoginRequiredMixin, TemplateView):
    template_name = 'cpashop/archived.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['orders'] = Order.objects.filter(thread__user=get_cpa_user(self.request))
        return data


class DiagramTemplateView(TemplateView):
    template_name = 'cpashop/diagram.html'


# ════════════════════════════════════════════════
# THREAD / MARKET (original: views/thread.py)
# ════════════════════════════════════════════════

class ThreadFormView(CpaLoginRequiredMixin, FormView):
    form_class = ThreadForm
    template_name = 'cpashop/thread/market-list.html'
    success_url = reverse_lazy('cpashop:thread-list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['products'] = Product.objects.all()
        data['categories'] = Category.objects.all()
        return data

    def form_valid(self, form):
        thread = form.save(commit=False)
        thread.user = get_cpa_user(self.request)
        thread.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)


class ThreadListView(CpaLoginRequiredMixin, ListView):
    queryset = Thread.objects.all()
    template_name = 'cpashop/thread/thread-list.html'
    context_object_name = 'threads'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['threads'] = data.get('threads').filter(user=get_cpa_user(self.request)).order_by('-created_at')
        return data


class ThreadProductDetailView(DetailView):
    """
    MUHIM TUZATISH: original loyihada bu view ham 'thread-list' nomi
    bilan ro'yxatdan o'tgan edi (list bilan BIR XIL nom — Django'da ikkita
    URL bir xil nomda bo'lsa, ikkinchisi birinchisini "soyalab" qo'yadi va
    reverse('thread-list') qaysi birini qaytarishi noaniq bo'lib qoladi).
    Bu — original kodda bo'lgan bug, men uni shu yerda nomini
    'thread-detail' deb o'zgartirib tuzatdim (cpashop/urls.py'ga qarang).
    """
    queryset = Thread.objects.all()
    template_name = 'cpashop/order/product-detail.html'
    context_object_name = 'thread'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        thread = data.get('thread')
        data['product'] = thread.product
        thread.visit_count += 1
        thread.save()
        return data


class ThreadStatisticTemplateView(CpaLoginRequiredMixin, TemplateView):
    template_name = 'cpashop/thread/thread-statistic.html'

    def get_context_data(self, **kwargs):
        now = datetime.datetime.now()
        map_range_date = {
            "last_day": (now - datetime.timedelta(days=1), now),
            "wekly": (now - datetime.timedelta(days=7), now),
            "last_month": (now - datetime.timedelta(days=30), now),
            "today": (now.replace(hour=0, minute=0, second=0, microsecond=0), now),
            "yesterday": (
                now - datetime.timedelta(days=1),
                now - datetime.timedelta(days=1, hours=23, minutes=59, seconds=59, microseconds=9999999),
            ),
        }
        period = self.request.GET.get('period')
        date = map_range_date.get(period)
        data = super().get_context_data(**kwargs)
        cpa_user = get_cpa_user(self.request)
        statistics = Thread.objects.filter(user=cpa_user)
        if date:
            statistics = statistics.filter(orders__ordered_at__range=date)
        statistics = statistics.annotate(
            new_count=Count('orders', filter=Q(orders__status=Order.StatusType.NEW)),
            ready_to_order_count=Count('orders', filter=Q(orders__status=Order.StatusType.READY_TO_ORDER)),
            delivering_count=Count('orders', filter=Q(orders__status=Order.StatusType.DELIVERING)),
            delivered_count=Count('orders', filter=Q(orders__status=Order.StatusType.DELIVERED)),
            not_pick_up_count=Count('orders', filter=Q(orders__status=Order.StatusType.NOT_PICK_UP)),
            canceled_count=Count('orders', filter=Q(orders__status=Order.StatusType.CANCELED)),
            archived_count=Count('orders', filter=Q(orders__status=Order.StatusType.ARCHIVED)),
        ).only('name', 'product__name', "visit_count")
        tmp = statistics.aggregate(
            all_visit_count=Sum('visit_count'),
            all_new_count=Sum('new_count'),
            all_ready_to_order_count=Sum('ready_to_order_count'),
            all_delivering_count=Sum('delivering_count'),
            all_delivered_count=Sum('delivered_count'),
            all_not_pick_up_count=Sum('not_pick_up_count'),
            all_canceled_count=Sum('canceled_count'),
            all_archived_count=Sum('archived_count'),
        )
        data['statistics'] = statistics
        data['thread_count'] = statistics.count()
        data.update(tmp)
        return data


class MarketListView(ListView):
    queryset = Category.objects.all()
    template_name = 'cpashop/thread/market-list.html'
    context_object_name = "categories"

    def get_context_data(self, *, object_list=None, **kwargs):
        slug = self.request.GET.get('category')
        data = super().get_context_data(**kwargs)
        products = Product.objects.all()
        if slug and slug != "all":
            products = products.filter(category__slug=slug)
        data['products'] = products
        data['slug'] = slug
        return data


# ════════════════════════════════════════════════
# ORDER (original: views/order.py)
# ════════════════════════════════════════════════

class OrderFormView(FormView):
    """Xaridor RO'YXATDAN O'TMASDAN ham buyurtma bera oladi (owner NULL qoladi)."""
    form_class = OrderForm
    template_name = 'cpashop/order/order-success.html'
    success_url = reverse_lazy('cpashop:order')

    def form_valid(self, form):
        cpa_user = get_cpa_user(self.request)
        order = form.save(cpa_user=cpa_user)
        deliver_price = AdminSetting.objects.first().deliver_price if AdminSetting.objects.first() else 0
        return render(self.request, 'cpashop/order/order-success.html',
                      context={'order': order, 'deliver_price': deliver_price})


class ProductDetailView(DetailView):
    queryset = Product.objects.all()
    template_name = 'cpashop/order/product-detail.html'
    slug_url_kwarg = 'slug'
    context_object_name = 'product'


class OrderListView(CpaLoginRequiredMixin, ListView):
    queryset = Order.objects.all()
    template_name = 'cpashop/order/order-list.html'
    context_object_name = 'orders'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['orders'] = data.get('orders').filter(owner=get_cpa_user(self.request))
        return data


class OrderUpdateView(CpaLoginRequiredMixin, UpdateView):
    queryset = Order.objects.all()
    form_class = OrderModelForm
    template_name = 'cpashop/operator/order-change.html'
    success_url = reverse_lazy('cpashop:operator')
    pk_url_kwarg = 'pk'

    def form_valid(self, form):
        obj = self.get_object(self.get_queryset())
        status = form.cleaned_data.get('status')
        if obj.status != status and status == 'completed':
            if obj.thread:
                # DIQQAT: original koddagi kabi to'g'ridan-to'g'ri balans
                # o'zgartirilmoqda (fayl boshidagi izohga qarang).
                user = obj.thread.user
                user.balance += obj.thread.product.sell_price - obj.thread.discount_sum
                user.save()
        return super().form_valid(form)


# ════════════════════════════════════════════════
# OPERATOR (original: views/operator.py)
# ════════════════════════════════════════════════

class OperatorTemplateView(CpaLoginRequiredMixin, TemplateView):
    template_name = 'cpashop/operator/operator-page.html'

    def dispatch(self, request, *args, **kwargs):
        cpa_user = get_cpa_user(request)
        if cpa_user and cpa_user.role not in ['operator', 'deliver']:
            return redirect('cpashop:home')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = self.get_context_data()
        return render(request, 'cpashop/operator/operator-page.html', data)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        cpa_user = get_cpa_user(self.request)
        status = self.request.GET.get('status')
        category_id = self.request.POST.get('category_id')
        district_id = self.request.POST.get('district_id')
        data['categories'] = Category.objects.all()
        data['regions'] = Region.objects.all()
        actions_map = {
            "operator": ['new', 'pending', 'canceled', 'not_pick_up', 'archived'],
            'deliver': ['delivering', 'delivered', 'completed', 'ready_to_order'],
        }
        orders = Order.objects.all()
        if status:
            if status == 'new':
                orders = orders.filter(status=status)
            else:
                orders = orders.filter(operator=cpa_user, status=status)
        else:
            if cpa_user and cpa_user.role == 'deliver':
                orders = orders.filter(status='ready_to_order')

        if category_id:
            orders = orders.filter(product__category_id=category_id)
        if district_id:
            orders = orders.filter(district_id=district_id)
        data['status'] = actions_map.get(cpa_user.role) if cpa_user else []
        data['orders'] = orders
        return data


class OperatorOrderChangeDetailView(CpaLoginRequiredMixin, DetailView):
    queryset = Order.objects.all()
    template_name = 'cpashop/operator/order-change.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'order'

    def get(self, request, *args, **kwargs):
        cpa_user = get_cpa_user(request)
        order_id = self.kwargs.get('pk')
        if cpa_user.role == 'deliver':
            Order.objects.filter(pk=order_id).update(deliver=cpa_user)
        else:
            Order.objects.filter(pk=order_id).update(operator=cpa_user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        return data


# ════════════════════════════════════════════════
# PAYMENTS (original: views/payments.py)
# ════════════════════════════════════════════════

class PaymentFormView(CpaLoginRequiredMixin, FormView):
    form_class = PaymentModelForm
    success_url = reverse_lazy('cpashop:payment')
    template_name = 'cpashop/payment/payment.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['payments'] = get_cpa_user(self.request).payments.all()
        return data

    def form_valid(self, form):
        cpa_user = get_cpa_user(self.request)
        amount = form.cleaned_data['amount']
        if amount > cpa_user.balance:
            form.add_error('amount', "Mablag' yetarli emas")
            return self.form_invalid(form)
        # DIQQAT: original koddagi kabi to'g'ridan-to'g'ri balans
        # o'zgartirilmoqda (fayl boshidagi izohga qarang).
        cpa_user.balance -= amount
        cpa_user.save()
        payment = form.save(commit=False)
        payment.user = cpa_user
        payment.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)
