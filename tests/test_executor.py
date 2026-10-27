"""Tests for executor.py"""

import pytest
from django.test import override_settings


@pytest.mark.django_db
class TestExecuteTaskFromPayload:
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
    def test_execute_task_successfully(self):
        from django.tasks.base import TaskResultStatus

        from django_tasks_cloud_tasks.executor import execute_task_from_payload
        from tests.tasks import add_numbers

        payload = {
            "task_id": "test-task-id-123",
            "task_path": f"{add_numbers.module_path}",
            "args": [5, 3],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        task_result, success = execute_task_from_payload(payload, "worker-123")

        assert success is True
        assert task_result.status == TaskResultStatus.SUCCESSFUL
        assert task_result.return_value == 8
        assert task_result.id == "test-task-id-123"

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
    def test_execute_task_with_failure(self):
        from django.tasks.base import TaskResultStatus

        from django_tasks_cloud_tasks.executor import execute_task_from_payload
        from tests.tasks import failing_task

        payload = {
            "task_id": "test-task-id-456",
            "task_path": f"{failing_task.module_path}",
            "args": [],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        task_result, success = execute_task_from_payload(payload, "worker-456")

        assert success is False
        assert task_result.status == TaskResultStatus.FAILED
        assert len(task_result.errors) == 1
        assert "ValueError" in task_result.errors[0].exception_class_path

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
    def test_execute_task_with_context(self):
        from django.tasks.base import TaskResultStatus

        from django_tasks_cloud_tasks.executor import execute_task_from_payload
        from tests.tasks import task_with_context

        payload = {
            "task_id": "test-task-id-789",
            "task_path": f"{task_with_context.module_path}",
            "args": ["Hello"],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": True,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        task_result, success = execute_task_from_payload(payload, "worker-789")

        assert success is True
        assert task_result.status == TaskResultStatus.SUCCESSFUL
        assert "test-task-id-789" in task_result.return_value
        assert "Hello" in task_result.return_value
