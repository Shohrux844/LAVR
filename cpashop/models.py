
from django.db.models import (
    Model, CharField, ForeignKey, DecimalField, ImageField, DateTimeField,
    CASCADE, TextField, IntegerField, SET_NULL, BigIntegerField, TextChoices,
    SlugField, SmallIntegerField, DateField, BooleanField,
)
from django.utils.text import slugify


class BaseSlugModel(Model):
    name = CharField(max_length=255)
    slug = SlugField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        if not self.slug:
            slug = slugify(self.name)
            i = 1
            base = slug
            while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save()


class CpaUser(Model):
    """
    Asl loyihadagi User(AbstractUser) o'rnini bosadi — lekin Django
    autentifikatsiya tizimidan MUSTAQIL (AUTH_USER_MODEL emas).
    Login/parol boshqaruvi cpashop/auth.py orqali, session asosida.
    """
    class RoleType(TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'
        OPERATOR = 'operator', 'Operator'
        DELIVER = 'deliver', 'Deliver'

    phone_number = CharField(max_length=20, unique=True)
    password = CharField(max_length=255)  # make_password() bilan hash qilingan holda saqlanadi
    first_name = CharField(max_length=150, blank=True)
    last_name = CharField(max_length=150, blank=True)
    district = ForeignKey('cpashop.District', on_delete=SET_NULL, null=True, blank=True)
    address = TextField(blank=True)
    telegram_id = BigIntegerField(unique=True, blank=True, null=True)
    about = TextField(blank=True, null=True)
    role = CharField(max_length=10, choices=RoleType.choices, default=RoleType.USER)
    balance = DecimalField(max_digits=10, decimal_places=0, default=0)
    date_created = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone_number

    class Meta:
        verbose_name = "CPA foydalanuvchi"
        verbose_name_plural = "CPA foydalanuvchilar"


class Region(Model):
    name = CharField(max_length=255)

    def __str__(self):
        return self.name


class District(Model):
    name = CharField(max_length=255)
    region = ForeignKey('cpashop.Region', on_delete=CASCADE)

    def __str__(self):
        return self.name


class Category(BaseSlugModel):
    icon = CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"


class Product(BaseSlugModel):
    """
    MUHIM: bu — cpashop'ning O'Z, MUSTAQIL Product modeli. SavdoTizim'ning
    apps.Product'i bilan HECH QANDAY bog'liqligi yo'q (ataylab shunday —
    siz "loyihani o'zini alohida qo'shish" so'ragan edingiz). Ikkala
    "Product" nomi bir loyihada erkin yashaydi, chunki ular turli app'larga
    tegishli (apps.Product va cpashop.Product).
    """
    description = TextField()
    price = DecimalField(max_digits=10, decimal_places=2)
    image = ImageField(upload_to='cpashop/products/')
    category = ForeignKey('cpashop.Category', on_delete=CASCADE)
    sell_price = DecimalField(max_digits=10, decimal_places=0)
    quantity = SmallIntegerField(default=1)
    sale = CharField(max_length=50, default=None, null=True, blank=True)
    telegram_url = CharField(max_length=50, null=True, blank=True)
    discount = SmallIntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mahsulot (CPA)"
        verbose_name_plural = "Mahsulotlar (CPA)"


class Wishlist(Model):
    user = ForeignKey('cpashop.CpaUser', on_delete=CASCADE)
    product = ForeignKey('cpashop.Product', on_delete=CASCADE)

    class Meta:
        verbose_name = "Sevimli"
        verbose_name_plural = "Sevimlilar"


class Thread(Model):
    """Mahsulot uchun ulashish (referal) linki — asl loyihadagi g'oya bilan bir xil."""
    user = ForeignKey('cpashop.CpaUser', on_delete=CASCADE)
    product = ForeignKey('cpashop.Product', on_delete=CASCADE)
    discount_sum = DecimalField(max_digits=10, decimal_places=2, default=0)
    name = CharField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)
    visit_count = IntegerField(default=0)

    @property
    def product_price(self):
        return self.product.price - self.discount_sum

    def __str__(self):
        return f"{self.user} — {self.product.name} ({self.name})"

    class Meta:
        verbose_name = "Ulashish linki"
        verbose_name_plural = "Ulashish linklari"
        ordering = ['-created_at']


class Order(Model):
    class StatusType(TextChoices):
        NEW = 'new', 'New'
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        CANCELED = 'canceled', 'Canceled'
        READY_TO_ORDER = 'ready_to_order', 'Ready To Order'
        DELIVERING = 'delivering', 'Delivering'
        DELIVERED = 'delivered', 'Delivered'
        ARCHIVED = 'archived', 'Archived'
        NOT_PICK_UP = 'not_pick_up', 'Not Pick Up'

    last_name = CharField(max_length=255)
    owner = ForeignKey('cpashop.CpaUser', on_delete=SET_NULL, null=True, blank=True, related_name='orders')
    phone_number = CharField(max_length=20)
    ordered_at = DateTimeField(auto_now_add=True)
    thread = ForeignKey('cpashop.Thread', on_delete=SET_NULL, null=True, blank=True, related_name='orders')
    product = ForeignKey('cpashop.Product', on_delete=CASCADE, related_name='orders')
    quantity = IntegerField(default=1)
    status = CharField(max_length=20, choices=StatusType.choices, default=StatusType.NEW)
    amount = DecimalField(max_digits=10, decimal_places=0, default=0, null=True, blank=True)
    updated_at = DateTimeField(auto_now=True)
    district = ForeignKey('cpashop.District', on_delete=SET_NULL, related_name='orders', null=True, blank=True)
    comment_operator = TextField(blank=True, null=True)
    send_date = DateTimeField(null=True, blank=True)
    operator = ForeignKey('cpashop.CpaUser', on_delete=SET_NULL, null=True, blank=True, related_name='sell_orders')
    deliver = ForeignKey('cpashop.CpaUser', on_delete=SET_NULL, null=True, blank=True, related_name='deliver_orders')

    @property
    def discount_sum(self):
        summa = self.product.discount * self.product.price / 100
        if self.thread:
            summa += self.thread.discount_sum
        return summa

    @property
    def amount_summa(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"Order #{self.pk} — {self.last_name}"

    class Meta:
        verbose_name = "Buyurtma (CPA)"
        verbose_name_plural = "Buyurtmalar (CPA)"
        ordering = ['-ordered_at']


class Payment(Model):
    class StatusType(TextChoices):
        REVIEW = 'review', 'Review'
        COMPLETED = 'completed', 'Completed'
        CANCEL = 'cancel', 'Cancel'

    user = ForeignKey('cpashop.CpaUser', on_delete=CASCADE, related_name='payments')
    amount = DecimalField(max_digits=10, decimal_places=2)
    payment_at = DateTimeField(auto_now_add=True)
    status = CharField(max_length=10, choices=StatusType.choices, default=StatusType.REVIEW)
    description = TextField(blank=True, null=True)
    card_number = CharField(max_length=16, blank=True, null=True)
    check_payment = ImageField(upload_to='cpashop/payments/check/', null=True, blank=True)

    def __str__(self):
        return f"{self.user} — {self.amount} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Pul yechish (CPA)"
        verbose_name_plural = "Pul yechishlar (CPA)"
        ordering = ['-payment_at']


class AdminSetting(Model):
    deliver_price = DecimalField(max_digits=5, decimal_places=0)
    competition_photo = ImageField(upload_to='cpashop/admin/')
    start = DateField()
    finish = DateField()
    description = TextField()

    class Meta:
        verbose_name = "CPA sozlamalari"
        verbose_name_plural = "CPA sozlamalari"
