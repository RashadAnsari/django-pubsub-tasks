import os
from pathlib import Path

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

# Outside DEBUG an unset key leaves SECRET_KEY empty, and Django refuses to start.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "secret" if DEBUG else "")

BASE_DIR = Path(__file__).resolve().parent.parent

if DEBUG:
    os.environ.setdefault("PUBSUB_EMULATOR_HOST", "localhost:8532")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

PUBSUB_PROJECT_ID = os.environ.get("PUBSUB_PROJECT_ID", "test-project")
PUBSUB_DEAD_LETTER_TOPIC = os.environ.get("PUBSUB_DEAD_LETTER_TOPIC", "test-dlq")
# Must match max_delivery_attempts on the subscriptions' dead-letter policy.
PUBSUB_MAX_DELIVERY_ATTEMPTS = int(os.environ.get("PUBSUB_MAX_DELIVERY_ATTEMPTS", "5"))
# Base URL the push subscriptions call; used by the create_local_pubsub command.
PUBSUB_PUSH_BASE_URL = os.environ.get("PUBSUB_PUSH_BASE_URL", "http://host.docker.internal:8000/tasks")
# Push requests are verified against these unless PUBSUB_EMULATOR_HOST is set.
PUBSUB_PUSH_AUDIENCE = os.environ.get("PUBSUB_PUSH_AUDIENCE")
PUBSUB_PUSH_SERVICE_ACCOUNT = os.environ.get("PUBSUB_PUSH_SERVICE_ACCOUNT")

INSTALLED_APPS = [
    "django_pubsub_tasks",
    "example",
    "simple_history",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "example.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "example.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
