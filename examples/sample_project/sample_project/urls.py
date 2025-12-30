"""
URL configuration for sample_project project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Cloud Tasks のタスク実行エンドポイント
    path("tasks/", include("django_tasks_cloud_tasks.urls")),
    # サンプルアプリ
    path("", include("sample_app.urls")),
]
