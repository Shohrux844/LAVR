import os
from pathlib import Path
from decouple import Config, RepositoryEnv, Csv

from django.contrib import messages

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── .env faylini ANIQ joydan o'qish (avtomatik qidirishga tayanmaymiz) ───
ENV_PATH = BASE_DIR / '.env'

if not ENV_PATH.exists():
    raise FileNotFoundError(
        f".env fayli topilmadi: {ENV_PATH}\n"
        f"Uni manage.py bilan BIR XIL papkaga joylashtiring. "
        f"Namuna uchun .env.example fayliga qarang."
    )

config = Config(RepositoryEnv(str(ENV_PATH)))

# ─── Maxfiy sozlamalar ──────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',
    'apps',
    'agent',
    'client',
    'cpashop'
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "lavr.urls"
AUTH_USER_MODEL = "apps.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cpashop.auth.cpashop_context_processor",  # ← YANGI
            ],
        },
    },
]

WSGI_APPLICATION = "lavr.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
# ESLATMA: SQLite select_for_update() bilan row-level lock qilmaydi —
# butun DB'ni qulflaydi. order_create/order_request_approve kabi
# tranzaksiyalar parallel ishlaganda "database is locked" xatosi chiqishi
# mumkin. Productionga chiqishdan oldin PostgreSQL'ga o'tish tavsiya etiladi:
#
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": config('DB_NAME'),
#         "USER": config('DB_USER'),
#         "PASSWORD": config('DB_PASSWORD'),
#         "HOST": config('DB_HOST', default='localhost'),
#         "PORT": config('DB_PORT', default='5432'),
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"

# TUZATILDI: avval "UTC" edi. Loyiha O'zbekistonda ishlaydi (Toshkent),
# date.today() / "bugungi savdo" kabi hisoblar UTC bo'yicha noto'g'ri
# chegara olishi mumkin edi (masalan UTC 19:00 — Toshkentda allaqachon
# ertangi kun). Endi barcha "bugun/hafta/oy" hisoblari mahalliy vaqt
# bo'yicha to'g'ri ishlaydi.
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [BASE_DIR / "static_src"]  # umumiy CSS shu yerga chiqariladi

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

from django.contrib.messages import constants as messages_constants

MESSAGE_TAGS = {
    messages_constants.DEBUG: 'info',
    messages_constants.INFO: 'info',
    messages_constants.SUCCESS: 'success',
    messages_constants.WARNING: 'warning',
    messages_constants.ERROR: 'error',
}

# ─── Telegram ────────────────────────────────────
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default='')

# ─── Email (parolni tiklash uchun) ───────────────
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)

# ─── Production xavfsizlik ───────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# ─── YANGI: LOGGING ───────────────────────────────
# Avval umuman logging konfiguratsiyasi yo'q edi — production'da xato
# yuz berganda (masalan Telegram API ishlamay qolsa, Excel eksport
# buzilsa) buni hech qayerda ko'rib bo'lmas edi. Endi:
#   - DEBUG=True bo'lsa: konsolga chiqadi (development)
#   - DEBUG=False bo'lsa: logs/django.log fayliga yoziladi (5MB x 5 rotatsiya)
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'] if DEBUG else ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'] if DEBUG else ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Telegram, sklad va sklad-eslatma modullari uchun alohida
        # kuzatuv — bular jim ishlaydigan (background thread, cron)
        # joylar, shuning uchun log ayniqsa muhim.
        'apps.telegram_bot': {
            'handlers': ['console'] if DEBUG else ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
