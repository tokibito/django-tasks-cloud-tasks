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
            "CLOUD_TASKS_PROJECT": "test-project",
            "CLOUD_TASKS_LOCATION": "us-central1",
            "TASK_HANDLER_HOST": "https://test.example.com",
        },
    },
}
