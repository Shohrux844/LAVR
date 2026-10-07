
from functools import wraps

from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect

from .models import CpaUser

SESSION_KEY = '_cpashop_user_id'


def cpa_login(request, user: CpaUser):
    request.session[SESSION_KEY] = user.pk


def cpa_logout(request):
    request.session.pop(SESSION_KEY, None)


def authenticate_cpa_user(phone_number, raw_password):
    """Telefon+parol bo'yicha CpaUser'ni tekshiradi, topilsa obyektni qaytaradi."""
    try:
        user = CpaUser.objects.get(phone_number=phone_number)
    except CpaUser.DoesNotExist:
        return None
    if check_password(raw_password, user.password):
        return user
    return None


def get_cpa_user(request):
    """Joriy so'rovdagi CpaUser'ni qaytaradi, yo'q bo'lsa — None."""
    user_id = request.session.get(SESSION_KEY)
    if not user_id:
        return None
    return CpaUser.objects.filter(pk=user_id).first()


def cpashop_context_processor(request):
    """
    Har bir shablonga `cpa_user` o'zgaruvchisini qo'shadi — asl CPA
    shablonlarida `request.user` o'rniga ishlatiladigan nom shu.
    settings.py TEMPLATES OPTIONS['context_processors'] ga qo'shiladi.
    """
    return {'cpa_user': get_cpa_user(request)}


def cpa_login_required(view_func):
    """Function-based view'lar uchun dekorator."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not get_cpa_user(request):
            return redirect('cpashop:auth')
        return view_func(request, *args, **kwargs)
    return wrapper


def cpa_operator_required(view_func):
    """Faqat role='operator' yoki 'deliver' bo'lgan CpaUser uchun."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = get_cpa_user(request)
        if not user or user.role not in (CpaUser.RoleType.OPERATOR, CpaUser.RoleType.DELIVER):
            return redirect('cpashop:home')
        return view_func(request, *args, **kwargs)
    return wrapper
