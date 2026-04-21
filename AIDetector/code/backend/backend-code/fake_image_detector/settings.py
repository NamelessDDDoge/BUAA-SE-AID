"""
Django settings for fake_image_detector project.
"""

import os
from datetime import timedelta
from pathlib import Path

from .database import build_database_settings


BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_DIR.parent.parent


def load_env_file(*paths: Path) -> None:
    for env_path in paths:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default=None):
    return os.environ.get(name, default)


def env_bool(name: str, default: bool) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = env(name)
    return int(value) if value not in (None, "") else default


load_env_file(PROJECT_DIR / ".env", PROJECT_DIR.parent / ".env")


SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-_v)h&d+^b=y_^u+di=au%*yf(u&j2nx((pcflfls*c1fn**3!d",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [item.strip() for item in env("DJANGO_ALLOWED_HOSTS", "*").split(",") if item.strip()]


INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fake_image_detector.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
            ],
        },
    },
]

WSGI_APPLICATION = "fake_image_detector.wsgi.application"


DATABASES = build_database_settings(PROJECT_DIR, env, env_bool, env_int)


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "allstatic"
MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "core.views.views_user.EmailBackend",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
}

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "smtp.qq.com")
EMAIL_PORT = env_int("EMAIL_PORT", 465)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "demo@example.com")

BAIDU_FANYI_APP_ID = env("BAIDU_FANYI_APP_ID", "")
BAIDU_FANYI_APP_KEY = env("BAIDU_FANYI_APP_KEY", "")
ENABLE_FANYI = env_bool("ENABLE_FANYI", False)

AI_SERVICE_DIR = env(
    "AI_SERVICE_DIR",
    str((CODE_DIR / "ai-service" / "ai-service-code").resolve()),
)
AI_TEST_DIR = env("AI_TEST_DIR", str((Path(AI_SERVICE_DIR) / "test").resolve()))
