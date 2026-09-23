from django.contrib import admin

from client.models import OrderRequest, OrderRequestItem, Cliente


class OrderRequestItemInline(admin.TabularInline):
    model = OrderRequestItem
    extra = 0


@admin.register(OrderRequest)
class OrderRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'cliente', 'status', 'date_created']
    list_filter = ['status']
    inlines = [OrderRequestItemInline]


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'firma_name', 'alternative_name', 'phone', 'agent', 'is_active']
    search_fields = ['first_name', 'last_name', 'firma_name', 'alternative_name', 'phone']
    list_filter = ['is_active', 'agent']
