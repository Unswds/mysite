"""
Django settings for config project.
생성: django-admin startproject (Django 4.0.3 기준)
"""

# ──────────────────────────── 공통 상단부 ────────────────────────────
from pathlib import Path
from dotenv import load_dotenv
import os, sys, json, base64
from google.oauth2 import service_account   # ← Vision 외에 필요 없으면 삭제 OK
from google.cloud import vision_v1

# 1) 프로젝트 루트 (…/manage.py 위치)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")      

# ── Google Vision creds 로딩 ─────────────────────────
import os, base64, json
from google.oauth2 import service_account

b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
if not b64:
    raise RuntimeError("GOOGLE_CREDENTIALS_B64 가 .env 에 필요합니다")

VISION_CREDENTIALS = service_account.Credentials.from_service_account_info(
    json.loads(base64.b64decode(b64))
)
print("✓ Google creds: loaded from B64")

# ───── Django 기본 환경 변수 ───────────────────────────────────────
SECRET_KEY    = os.getenv("DJANGO_SECRET_KEY")
DEBUG         = os.getenv("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# ───── Email (Gmail SMTP 예시) ─────────────────────────────────────
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = "smtp.gmail.com"
EMAIL_PORT          = 587
EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS       = True
DEFAULT_FROM_EMAIL  = EMAIL_HOST_USER

# ───── OpenAI & Google Vision 키 ──────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ───── 필수 값 누락 시 즉시 실패 ───────────────────────────────────
_missing = []
for k, v in {
    "DJANGO_SECRET_KEY": SECRET_KEY,
    "OPENAI_API_KEY":    OPENAI_API_KEY,
}.items():
    if not v:
        _missing.append(k)
if _missing:
    print("\n✖ 누락 환경 변수/파일:", ", ".join(_missing), file=sys.stderr)
    raise RuntimeError("필수 환경 변수를 설정하세요")

# ─────────────────────── 여기부터 기존 설정 유지 ─────────────────────
# Application definition -------------------------------------------------
INSTALLED_APPS = [
    "common.apps.CommonConfig",
    "pybo.apps.PyboConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database ---------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Password validation ----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization ---------------------------------------------------
LANGUAGE_CODE = "ko-kr"
TIME_ZONE     = "Asia/Seoul"
USE_I18N      = True
USE_TZ        = True

# Static & Media ---------------------------------------------------------
STATIC_URL       = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Auth redirect 설정 -----------------------------------------------------
LOGIN_URL          = "common:auth_portal"
LOGIN_REDIRECT_URL = "pybo:main"
LOGOUT_REDIRECT_URL = "pybo:main"

# Primary key type -------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
