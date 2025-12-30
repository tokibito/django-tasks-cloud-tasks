"""Tests for backends.py"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


class TestCloudTasksBackendInit:
    def test_raises_error_when_project_id_not_configured(self):
        from django_tasks_cloud_tasks.backends import CloudTasksBackend

        with patch(
            "django_tasks_cloud_tasks.detection.detect_gcp_project", return_value=None
        ):
            with patch(
                "django_tasks_cloud_tasks.detection.detect_gcp_location",
                return_value="us-central1",
            ):
                with patch(
                    "django_tasks_cloud_tasks.detection.detect_task_handler_host",
                    return_value="https://test.example.com",
                ):
                    with patch(
                        "django_tasks_cloud_tasks.detection.detect_default_service_account",
                        return_value=None,
                    ):
                        with pytest.raises(ImproperlyConfigured) as exc_info:
                            CloudTasksBackend("default", {"OPTIONS": {}})
                        assert "CLOUD_TASKS_PROJECT is required" in str(exc_info.value)

    def test_raises_error_when_location_not_configured(self):
        from django_tasks_cloud_tasks.backends import CloudTasksBackend

        with patch(
            "django_tasks_cloud_tasks.detection.detect_gcp_project",
            return_value="my-project",
        ):
            with patch(
                "django_tasks_cloud_tasks.detection.detect_gcp_location",
                return_value=None,
            ):
                with patch(
                    "django_tasks_cloud_tasks.detection.detect_task_handler_host",
                    return_value="https://test.example.com",
                ):
                    with patch(
                        "django_tasks_cloud_tasks.detection.detect_default_service_account",
                        return_value=None,
                    ):
                        with pytest.raises(ImproperlyConfigured) as exc_info:
                            CloudTasksBackend("default", {"OPTIONS": {}})
                        assert "CLOUD_TASKS_LOCATION is required" in str(exc_info.value)

    def test_raises_error_when_service_url_not_configured(self):
        from django_tasks_cloud_tasks.backends import CloudTasksBackend

        with patch(
            "django_tasks_cloud_tasks.detection.detect_gcp_project",
            return_value="my-project",
        ):
            with patch(
                "django_tasks_cloud_tasks.detection.detect_gcp_location",
                return_value="us-central1",
            ):
                with patch(
                    "django_tasks_cloud_tasks.detection.detect_task_handler_host",
                    return_value=None,
                ):
                    with patch(
                        "django_tasks_cloud_tasks.detection.detect_default_service_account",
                        return_value=None,
                    ):
                        with pytest.raises(ImproperlyConfigured) as exc_info:
                            CloudTasksBackend("default", {"OPTIONS": {}})
                        assert "TASK_HANDLER_HOST is required" in str(exc_info.value)

    def test_initializes_with_valid_options(self):
        from django_tasks_cloud_tasks.backends import CloudTasksBackend

        with patch(
            "django_tasks_cloud_tasks.detection.detect_default_service_account",
            return_value=None,
        ):
            backend = CloudTasksBackend(
                "default",
                {
                    "QUEUES": ["default"],
                    "OPTIONS": {
                        "CLOUD_TASKS_PROJECT": "my-project",
                        "CLOUD_TASKS_LOCATION": "asia-northeast1",
                        "TASK_HANDLER_HOST": "https://my-app.run.app",
                    },
                },
            )

            assert backend.project_id == "my-project"
            assert backend.location == "asia-northeast1"
            assert backend.task_handler_host == "https://my-app.run.app"
            assert backend.supports_defer is True
            assert backend.supports_async_task is True
            assert backend.supports_get_result is False
            assert backend.supports_priority is False


@pytest.mark.django_db
class TestCloudTasksBackendEnqueue:
    @override_settings(
        TASKS={
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
    )
    @patch("google.cloud.tasks_v2.CloudTasksClient")
    def test_enqueue_task(self, mock_client_class):
        from django.tasks.base import TaskResultStatus

        from tests.tasks import add_numbers

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = add_numbers.enqueue(1, 2)

        assert result.status == TaskResultStatus.READY
        assert result.args == [1, 2]
        assert result.kwargs == {}
        mock_client.create_task.assert_called_once()

    @override_settings(
        TASKS={
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
    )
    @patch("google.cloud.tasks_v2.CloudTasksClient")
    def test_enqueue_task_with_kwargs(self, mock_client_class):
        from django.tasks.base import TaskResultStatus

        from tests.tasks import message_task

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = message_task.enqueue("hello", count=3)

        assert result.status == TaskResultStatus.READY
        assert result.args == ["hello"]
        assert result.kwargs == {"count": 3}
        mock_client.create_task.assert_called_once()
