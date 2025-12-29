"""URL configuration."""

from django.urls import path

from .views import ExecuteTaskView

app_name = "django_tasks_cloud_tasks"

urlpatterns = [
    path("execute/", ExecuteTaskView.as_view(), name="execute_task"),
]
