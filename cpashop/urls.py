
from django.urls import path

from . import views

app_name = 'cpashop'

urlpatterns = [
    # ─── Bosh sahifa / katalog ──────────────────────────
    path('', views.HomeListView.as_view(), name='home'),
    path('products/<str:slug>', views.ProductListView.as_view(), name='product-list'),
    path('wishlist/<int:pk>', views.WishlistView.as_view(), name='wishlist'),
    path('product/detail/<str:slug>', views.ProductDetailView.as_view(), name='product-detail'),
    path('like', views.LikeListView.as_view(), name='like'),
    path('product/sell', views.ProductSellListView.as_view(), name='product-sell'),
    path('competition', views.CompetitionListView.as_view(), name='competition'),
    path('archived', views.ArchivedTemplateView.as_view(), name='archived'),
    path('diagram', views.DiagramTemplateView.as_view(), name='diagram'),

    # ─── Auth (session-asosli, Django auth'dan mustaqil) ─
    path('auth', views.AuthFormView.as_view(), name='auth'),
    path('logout', views.CustomLogoutView.as_view(), name='logout'),
    path('profile', views.ProfileFormView.as_view(), name='profile'),
    path('district-list', views.district_list_view, name='district-list'),
    path('change-password', views.ChangePasswordFormView.as_view(), name='change-password'),

    # ─── Thread (ulashish linklari) / Market ────────────
    path('thread/form', views.ThreadFormView.as_view(), name='thread-form'),
    path('thread/list', views.ThreadListView.as_view(), name='thread-list'),
    path('thread/<int:pk>', views.ThreadProductDetailView.as_view(), name='thread-detail'),  # TUZATILDI
    path('thread/statistic', views.ThreadStatisticTemplateView.as_view(), name='thread-statistic'),
    path('market', views.MarketListView.as_view(), name='market'),

    # ─── Order ───────────────────────────────────────────
    path('order/form', views.OrderFormView.as_view(), name='order'),
    path('order/list', views.OrderListView.as_view(), name='order-list'),
    path('order/update/<int:pk>', views.OrderUpdateView.as_view(), name='order-update'),

    # ─── Operator ────────────────────────────────────────
    path('operator', views.OperatorTemplateView.as_view(), name='operator'),
    path('operator/order-change/<int:pk>', views.OperatorOrderChangeDetailView.as_view(), name='order-change'),

    # ─── To'lov (balans yechish) ─────────────────────────
    path('payment', views.PaymentFormView.as_view(), name='payment'),
]
