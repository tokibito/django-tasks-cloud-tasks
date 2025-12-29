"""Django settings for testing."""

SECRET_KEY = "test-secret-key-for-testing-only"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_tasks_cloud_tasks",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

# Task configuration (for testing)
TASKS = {
    "default": {
        "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
        "QUEUES": ["default"],
        "OPTIONS": {
            "PROJECT_ID": "test-project",
            "LOCATION": "us-central1",
            "SERVICE_URL": "https://test.example.com",
        },
    },
}
