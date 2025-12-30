"""
Django settings for sample_project project.

Settings file for sample project.
For local testing with Cloud Tasks emulator.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-sample-project-secret-key-for-development-only"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Cloud Tasks backend
    "django_tasks_cloud_tasks",
    # Sample app
    "sample_app",
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

ROOT_URLCONF = "sample_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sample_project.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "ja"

TIME_ZONE = "Asia/Tokyo"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# Django Tasks Configuration
# ============================================================

TASKS = {
    "default": {
        "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
        "QUEUES": ["default", "high-priority"],
        "OPTIONS": {
            # GCP project ID
            "CLOUD_TASKS_PROJECT": os.environ.get(
                "GOOGLE_CLOUD_PROJECT", "your-project-id"
            ),
            # Cloud Tasks location
            "CLOUD_TASKS_LOCATION": os.environ.get(
                "CLOUD_TASKS_LOCATION", "asia-northeast1"
            ),
            # Task execution endpoint base URL
            "TASK_HANDLER_HOST": os.environ.get("SERVICE_URL", "http://localhost:8000"),
            # Task execution endpoint path (default: /cloudtasks/execute/)
            # "TASK_HANDLER_PATH": "/cloudtasks/execute/",
            # OIDC authentication settings (configure for production)
            # "OIDC_SERVICE_ACCOUNT_EMAIL": "your-sa@your-project.iam.gserviceaccount.com",
            # "OIDC_AUDIENCE": "https://your-app.run.app",
        },
    },
}

# OIDC authentication audience (set to None in development to skip authentication)
CLOUD_TASKS_OIDC_AUDIENCE = os.environ.get("CLOUD_TASKS_OIDC_AUDIENCE", None)


# ============================================================
# Logging Configuration
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django_tasks_cloud_tasks": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
        "django.tasks": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}
