
import re

from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.forms import Form, IntegerField, DecimalField
from django.forms.fields import CharField
from django.forms.models import ModelForm

from .models import CpaUser, Order, Thread, Product, AdminSetting, Payment


class AuthForm(Form):
    """
    Original bilan bir xil: bitta forma orqali ham login, ham ro'yxatdan
    o'tish. Qaysi holat ekanligini VIEW hal qiladi (agar telefon
    bazada bor bo'lsa — parolni tekshirib login, aks holda — yangi
    CpaUser yaratib login).
    """
    phone_number = CharField(max_length=50)
    password = CharField(max_length=128)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        digits_only = "+" + re.sub(r"\D", "", phone_number)
        return digits_only

    def create_user(self):
        """Faqat YANGI foydalanuvchi uchun view tomonidan chaqiriladi."""
        phone_number = self.cleaned_data.get("phone_number")
        raw_password = self.cleaned_data.get("password")
        return CpaUser.objects.create(
            phone_number=phone_number,
            password=make_password(raw_password),
        )


class ProfileForm(Form):
    first_name = CharField(required=False)
    last_name = CharField(required=False)
    district_id = CharField(required=False)
    address = CharField(required=False)
    telegram_id = IntegerField(required=False)
    about = CharField(required=False)

    def update(self, cpa_user):
        data = self.cleaned_data.copy()
        district_id = data.pop('district_id', None)
        CpaUser.objects.filter(pk=cpa_user.pk).update(district_id=district_id or None, **data)


class ChangePasswordForm(Form):
    old = CharField(required=False)
    new = CharField(required=False)
    confirm = CharField(required=False)

    def clean_confirm(self):
        new = self.data.get('new')
        confirm = self.cleaned_data.get('confirm')
        if new != confirm:
            raise ValidationError("Parollar mos emas!")
        return confirm

    def clean_new(self):
        return make_password(self.cleaned_data.get('new'))

    def update(self, cpa_user):
        password = self.cleaned_data.get('new')
        CpaUser.objects.filter(pk=cpa_user.pk).update(password=password)


class OrderForm(Form):
    last_name = CharField(max_length=255)
    phone_number = CharField(max_length=20)
    product_id = IntegerField()
    thread_id = IntegerField(required=False)
    amount = DecimalField(max_digits=10, decimal_places=0, required=False)
    quantity = IntegerField(required=False, min_value=1)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        digits_only = "+" + re.sub(r"\D", "", phone_number)
        return digits_only

    def save(self, cpa_user=None):
        """
        cpa_user — ixtiyoriy (ro'yxatdan o'tmagan xaridor ham buyurtma
        bera oladi, owner NULL qoladi — Order.owner null=True, blank=True
        bo'lgani uchun bu xavfsiz).
        """
        setting = AdminSetting.objects.first()
        deliver_price = setting.deliver_price if setting else 0

        data = self.cleaned_data.copy()
        data.pop('quantity', None)
        quantity = self.cleaned_data.get('quantity') or 1

        order = Order.objects.create(
            **data,
            quantity=quantity,
            owner=cpa_user,
        )
        amount = order.product.price * order.quantity + deliver_price
        thread_id = self.cleaned_data.get('thread_id')
        if thread_id:
            thread = Thread.objects.filter(pk=thread_id).first()
            if thread:
                amount -= thread.discount_sum
        order.amount = amount
        order.save()
        return order


class ThreadForm(ModelForm):
    class Meta:
        model = Thread
        fields = ['name', 'discount_sum', 'product']

    def clean_discount_sum(self):
        product_id = self.data.get('product')
        product = Product.objects.filter(pk=product_id).first()
        discount_sum = self.cleaned_data.get('discount_sum')
        if discount_sum is None:
            discount_sum = 0
        if product and product.sell_price < discount_sum:
            raise ValidationError("Chegirma miqdori berilgandan ko'p")
        return discount_sum


class OrderModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment_operator'].required = False
        self.fields['quantity'].required = False
        self.fields['send_date'].required = False
        self.fields['district'].required = False
        self.fields['status'].required = False

    class Meta:
        model = Order
        fields = ['quantity', 'send_date', 'district', 'status', 'comment_operator']


class PaymentModelForm(ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'card_number']

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < 100000:
            raise ValidationError("Minimal yechib olish summasi 100 ming so'm!")
        return amount

    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number')
        if not card_number.isdigit() or len(card_number) != 16:
            raise ValidationError("Karta raqamida xatolik bor!")
        return card_number
