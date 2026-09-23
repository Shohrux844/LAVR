from django.contrib.auth.models import AbstractUser
from django.db.models import (
    Model,
    CharField,
    TextField,
    ForeignKey,
    CASCADE,
    SET_NULL,
    IntegerField,
    DecimalField,
    PositiveIntegerField,
    FloatField,
    ImageField,
    DateTimeField,
    DateField,
    BooleanField,
    TextChoices, OneToOneField,
)


# ──────────────────────────────────────────────
# 4. Mijoz (Cliente)
# ──────────────────────────────────────────────
class Cliente(Model):
    user = OneToOneField(
        'apps.User', on_delete=SET_NULL, null=True, blank=True,
        related_name='cliente_profile',
        help_text="Mijozning login hisobi (agar mijoz panelidan foydalansa)"
    )
    first_name = CharField(max_length=120)
    last_name = CharField(max_length=120)
    firma_name = CharField(max_length=120, blank=True)
    alternative_name = CharField(max_length=120, blank=True)
    phone = CharField(max_length=20, blank=True)
    address = CharField(max_length=255, blank=True)
    agent = ForeignKey('agent.Agent', on_delete=SET_NULL, null=True, related_name='clients')
    is_active = BooleanField(default=True)
    date_created = DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.firma_name or f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"


# ──────────────────────────────────────────────
# 12. Buyurtma so'rovi (mijoz tomonidan yuboriladi)
# ──────────────────────────────────────────────
class OrderRequest(Model):
    class Status(TextChoices):
        PENDING = 'pending', "Yangi so'rov"
        APPROVED = 'approved', "Tasdiqlangan"
        REJECTED = 'rejected', "Rad etilgan"

    cliente = ForeignKey("client.Cliente", on_delete=CASCADE, related_name='order_requests')
    status = CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    note = TextField(blank=True, help_text="Mijozning izohi")
    admin_note = TextField(blank=True, help_text="Admin izohi (masalan rad etish sababi)")
    order = ForeignKey(
        "apps.Order", on_delete=SET_NULL, null=True, blank=True,
        related_name='source_request',
        help_text="Tasdiqlangandan keyin yaratilgan nakladnoy"
    )
    date_created = DateTimeField(auto_now_add=True)
    date_reviewed = DateTimeField(null=True, blank=True)

    @property
    def total_sum(self):
        return sum(item.subtotal for item in self.items.all())

    def __str__(self):
        return f"So'rov #{self.pk} — {self.cliente}"

    class Meta:
        verbose_name = "Buyurtma so'rovi"
        verbose_name_plural = "Buyurtma so'rovlari"
        ordering = ['-date_created']


class OrderRequestItem(Model):
    request = ForeignKey("client.OrderRequest", on_delete=CASCADE, related_name='items')
    product = ForeignKey("apps.Product", on_delete=CASCADE, related_name='request_items')
    quantity = PositiveIntegerField(default=1)
    price = IntegerField(help_text="So'rov paytidagi narx")

    @property
    def subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    class Meta:
        verbose_name = "So'rov tovari"
        verbose_name_plural = "So'rov tovarlari"
