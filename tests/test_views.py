"""Tests for views.py"""

import json
import pytest
from unittest.mock import patch, MagicMock

from django.test import RequestFactory, override_settings


@pytest.mark.django_db
class TestExecuteTaskView:
    @override_settings(
        TASKS={
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
    )
    @patch("google.cloud.tasks_v2.CloudTasksClient")
    def test_execute_task_success(self, mock_client_class):
        from django_tasks_cloud_tasks.views import ExecuteTaskView
        from tests.tasks import simple_task

        factory = RequestFactory()
        payload = {
            "task_id": "view-test-task-123",
            "task_path": f"{simple_task.module_path}",
            "args": [5],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        request = factory.post(
            "/tasks/execute/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        view = ExecuteTaskView.as_view()
        response = view(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "success"
        assert data["task_id"] == "view-test-task-123"

    @override_settings(
        TASKS={
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
    )
    @patch("google.cloud.tasks_v2.CloudTasksClient")
    def test_execute_task_failure(self, mock_client_class):
        from django_tasks_cloud_tasks.views import ExecuteTaskView
        from tests.tasks import failing_view_task

        factory = RequestFactory()
        payload = {
            "task_id": "view-test-task-456",
            "task_path": f"{failing_view_task.module_path}",
            "args": [],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        request = factory.post(
            "/tasks/execute/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        view = ExecuteTaskView.as_view()
        response = view(request)

        # Return 500 for Cloud Tasks retry
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data["status"] == "failed"
        assert len(data["errors"]) == 1
        assert "RuntimeError" in data["errors"][0]["exception"]

    @override_settings(
        TASKS={
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
    )
    def test_invalid_json_returns_400(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        factory = RequestFactory()
        request = factory.post(
            "/tasks/execute/",
            data="invalid json",
            content_type="application/json",
        )

        view = ExecuteTaskView.as_view()
        response = view(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["error"] == "Invalid JSON"

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
                "QUEUES": ["default"],
                "OPTIONS": {
                    "PROJECT_ID": "test-project",
                    "LOCATION": "us-central1",
                    "SERVICE_URL": "https://test.example.com",
                },
            },
        },
        CLOUD_TASKS_OIDC_AUDIENCE="https://test.example.com",
    )
    def test_unauthorized_without_token(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        factory = RequestFactory()
        request = factory.post(
            "/tasks/execute/",
            data=json.dumps({}),
            content_type="application/json",
        )

        # Mock the auth handler to reject the request
        with patch(
            "django_tasks_cloud_tasks.auth.create_oidc_auth_handler"
        ) as mock_create:
            mock_handler = MagicMock(
                return_value=(False, "Missing or invalid Authorization header")
            )
            mock_create.return_value = mock_handler

            view = ExecuteTaskView.as_view()
            response = view(request)

            assert response.status_code == 401
            data = json.loads(response.content)
            assert data["error"] == "Unauthorized"
