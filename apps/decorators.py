"""
apps/decorators.py

Uch xil foydalanuvchi turi uchun ruxsat tekshiruvchi decoratorlar:
  - @admin_required  → faqat is_staff=True (admin/xodim)
  - @agent_required  → faqat Agent profiliga ega foydalanuvchi
  - @client_required → faqat Cliente profiliga ega foydalanuvchi

Ishlatilishi (@login_required o'rniga):
    from apps.decorators import admin_required

    @admin_required
    def order_list(request):
        ...
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect


def redirect_for_role(user):
    """
    Foydalanuvchi turiga qarab mos panel dashboard'iga yo'naltiradi.
    Login qilgandan keyin va ruxsatsiz sahifaga kirishga urinishda ishlatiladi.
    """
    if not user.is_authenticated:
        return redirect('login')
    if user.is_staff:
        return redirect('dashboard')
    if hasattr(user, 'agent_profile'):
        return redirect('agent_dashboard')
    if hasattr(user, 'cliente_profile'):
        return redirect('client_dashboard')
    return redirect('login')


def admin_required(view_func):
    """Faqat is_staff=True (admin/xodim) foydalanuvchilar kira oladi."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Bu sahifaga kirish huquqingiz yo'q.")
            return redirect_for_role(request.user)
        return view_func(request, *args, **kwargs)

    return wrapper


def agent_required(view_func):
    """Faqat Agent profiliga ega (agent sifatida ro'yxatdan o'tgan) foydalanuvchilar kira oladi."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'agent_profile'):
            messages.error(request, "Bu sahifaga kirish huquqingiz yo'q.")
            return redirect_for_role(request.user)
        return view_func(request, *args, **kwargs)

    return wrapper


def client_required(view_func):
    """Faqat Cliente profiliga ega (mijoz sifatida ro'yxatdan o'tgan) foydalanuvchilar kira oladi."""

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'cliente_profile'):
            messages.error(request, "Bu sahifaga kirish huquqingiz yo'q.")
            return redirect_for_role(request.user)
        return view_func(request, *args, **kwargs)

    return wrapper
