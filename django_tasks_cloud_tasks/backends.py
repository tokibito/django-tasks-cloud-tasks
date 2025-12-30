"""Cloud Tasks backend for Django tasks framework."""

import json

from django.core.exceptions import ImproperlyConfigured
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.base import TaskResult, TaskResultStatus
from django.tasks.signals import task_enqueued
from django.utils import timezone
from django.utils.crypto import get_random_string


class CloudTasksBackend(BaseTaskBackend):
    """
    Task backend using Google Cloud Tasks.

    Task parameters are stored in Cloud Tasks payload, not in database.
    """

    supports_defer = True  # Cloud Tasks supports deferred execution
    supports_async_task = True  # Async tasks are supported
    supports_get_result = False  # Result retrieval not supported (no DB storage)
    supports_priority = False  # Cloud Tasks does not support priority

    def __init__(self, alias, params):
        super().__init__(alias, params)

        from .detection import (
            detect_default_service_account,
            detect_gcp_location,
            detect_gcp_project,
            detect_task_handler_host,
        )

        # Get from options, or auto-detect
        # Use same option names as django-database-task for consistency
        self.project_id = self.options.get("CLOUD_TASKS_PROJECT") or detect_gcp_project()
        self.location = self.options.get("CLOUD_TASKS_LOCATION") or detect_gcp_location()
        self.task_handler_host = self.options.get("TASK_HANDLER_HOST") or detect_task_handler_host()
        self.task_handler_path = self.options.get("TASK_HANDLER_PATH", "/cloudtasks/execute/")

        # OIDC configuration
        self.oidc_service_account_email = (
            self.options.get("OIDC_SERVICE_ACCOUNT_EMAIL")
            or detect_default_service_account()
        )
        self.oidc_audience = self.options.get("OIDC_AUDIENCE") or self.task_handler_host

        # Validate required settings
        if not self.project_id:
            raise ImproperlyConfigured(
                "CLOUD_TASKS_PROJECT is required. Set it in OPTIONS or ensure "
                "GOOGLE_CLOUD_PROJECT environment variable is set."
            )
        if not self.location:
            raise ImproperlyConfigured(
                "CLOUD_TASKS_LOCATION is required. Set it in OPTIONS or ensure "
                "CLOUD_TASKS_LOCATION environment variable is set."
            )
        if not self.task_handler_host:
            raise ImproperlyConfigured(
                "TASK_HANDLER_HOST is required. Set it in OPTIONS or deploy to "
                "Cloud Run/App Engine for auto-detection."
            )

    def enqueue(self, task, args, kwargs):
        """Enqueue task to Cloud Tasks."""
        from google.cloud import tasks_v2
        from google.protobuf import timestamp_pb2

        self.validate_task(task)

        task_id = get_random_string(32)
        now = timezone.now()

        # Serialize task info (including all parameters)
        payload = {
            "task_id": task_id,
            "task_path": task.module_path,
            "args": list(args),
            "kwargs": dict(kwargs),
            "queue_name": task.queue_name,
            "backend": self.alias,
            "priority": task.priority,
            "takes_context": task.takes_context,
            "enqueued_at": now.isoformat(),
        }

        # Create task in Cloud Tasks
        # Use task.queue_name as Cloud Tasks queue ID
        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(self.project_id, self.location, task.queue_name)

        # Build task execution URL
        execute_url = f"{self.task_handler_host.rstrip('/')}{self.task_handler_path}"

        http_request = {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": execute_url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode(),
        }

        # Configure OIDC authentication
        if self.oidc_service_account_email:
            http_request["oidc_token"] = {
                "service_account_email": self.oidc_service_account_email,
                "audience": self.oidc_audience,
            }

        task_request = {"http_request": http_request}

        # Configure deferred execution
        if task.run_after:
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(task.run_after)
            task_request["schedule_time"] = timestamp

        # Create task in Cloud Tasks
        client.create_task(parent=parent, task=task_request)

        # Return TaskResult
        task_result = TaskResult(
            task=task,
            id=task_id,
            status=TaskResultStatus.READY,
            enqueued_at=now,
            started_at=None,
            finished_at=None,
            last_attempted_at=None,
            args=list(args),
            kwargs=dict(kwargs),
            backend=self.alias,
            errors=[],
            worker_ids=[],
        )

        # Send signal
        task_enqueued.send(sender=type(self), task_result=task_result)

        return task_result
