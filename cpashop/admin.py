
from django.contrib import admin
from django.utils.html import format_html

from .models import Product, Category, AdminSetting, Payment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(AdminSetting)
class AdminSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        max_instance = 1
        if self.model.objects.count() >= max_instance:
            return False
        return super().has_add_permission(request)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = 'id', 'user', 'card_number', 'amount', 'is_status', 'payment_at'

    def is_status(self, obj):
        if obj.status == 'review':
            fmt = format_html(
                '<img width="24" height="24" src="https://img.icons8.com/color/24/last-24-hours--v1.png" alt="review"/>'
            )
        elif obj.status == 'cancel':
            fmt = format_html(
                '<img width="24" height="24" src="https://img.icons8.com/fluency/24/cancel.png" alt="cancel"/>'
            )
        else:
            fmt = format_html(
                '<img width="24" height="24" src="https://img.icons8.com/color/24/ok--v1.png" alt="ok"/>'
            )
        return fmt

    is_status.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if change:
            if obj.status == 'cancel':
                # DIQQAT: original koddagi kabi to'g'ridan-to'g'ri balans
                # o'zgartirilmoqda — cpashop/views.py boshidagi izohga qarang.
                user = obj.user
                user.balance += obj.amount
                user.save()
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'completed':
            return ['status']
        return []
