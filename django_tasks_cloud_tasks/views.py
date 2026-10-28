"""Views for receiving requests from Cloud Tasks and executing tasks."""

import json
import logging

from django.http import JsonResponse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .executor import execute_task_from_payload, validate_payload

logger = logging.getLogger("django_tasks_cloud_tasks")


@method_decorator(csrf_exempt, name="dispatch")
class ExecuteTaskView(View):
    """
    View for receiving requests from Cloud Tasks and executing tasks.
    """

    # Alias of the task backend whose OIDC configuration authenticates the
    # requests. Authentication runs before the body is read, so it cannot
    # come from the "backend" field of the payload; that would also let a
    # request pick a backend without OIDC to skip the check. Set it with
    # ExecuteTaskView.as_view(backend_alias="...") for another alias.
    backend_alias = "default"

    def get_auth_handler(self):
        """
        Get authentication handler.

        The CLOUD_TASKS_OIDC_AUDIENCE setting, when set, turns verification
        on with that audience. Otherwise the token is verified whenever the
        backend has OIDC_SERVICE_ACCOUNT_EMAIL, given or detected, which is
        what makes Cloud Tasks send one, against the backend's
        OIDC_AUDIENCE, which is the audience it is sent with.

        Can be overridden in subclasses.
        """
        from django.conf import settings
        from django.tasks import task_backends

        from .auth import create_oidc_auth_handler

        audience = getattr(settings, "CLOUD_TASKS_OIDC_AUDIENCE", None)
        if audience:
            return create_oidc_auth_handler(audience)

        backend = task_backends[self.backend_alias]
        if getattr(backend, "oidc_service_account_email", None):
            return create_oidc_auth_handler(backend.oidc_audience)

        return None

    def post(self, request):
        # Authentication
        auth_handler = self.get_auth_handler()
        if auth_handler:
            is_valid, error_message = auth_handler(request)
            if not is_valid:
                logger.warning(f"Authentication failed: {error_message}")
                return JsonResponse(
                    {"error": "Unauthorized", "detail": error_message},
                    status=401,
                )

        # Parse request body
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError as e:
            return JsonResponse(
                {"error": "Invalid JSON", "detail": str(e)},
                status=400,
            )

        # A malformed payload cannot succeed, so it is answered 400 rather
        # than 500. Cloud Tasks retries any answer outside 2xx all the same;
        # that lets a revision that understands the payload pick it up when
        # it was enqueued by another version during a deploy.
        error_message = validate_payload(payload)
        if error_message:
            # Enough to find the cause from the log alone: what is wrong, the
            # task when it can be told, and the Cloud Tasks headers, which
            # say whether Cloud Tasks sent the request and which attempt it
            # is. The keys are logged and not the values, which may hold the
            # task's arguments.
            fields = payload if isinstance(payload, dict) else {}
            logger.error(
                "Invalid payload: detail=%s id=%s path=%s keys=%s queue=%s "
                "cloud_task=%s retry_count=%s",
                error_message,
                fields.get("task_id"),
                fields.get("task_path"),
                sorted(fields) if isinstance(payload, dict) else None,
                request.headers.get("X-CloudTasks-QueueName"),
                request.headers.get("X-CloudTasks-TaskName"),
                request.headers.get("X-CloudTasks-TaskRetryCount"),
            )
            return JsonResponse(
                {"error": "Invalid payload", "detail": error_message},
                status=400,
            )

        # Generate worker ID
        worker_id = get_random_string(32)

        # Execute task
        try:
            task_result, success = execute_task_from_payload(payload, worker_id)
        except Exception as e:
            logger.exception("Task execution failed")
            return JsonResponse(
                {"error": "Task execution failed", "detail": str(e)},
                status=500,
            )

        if success:
            return JsonResponse(
                {
                    "status": "success",
                    "task_id": task_result.id,
                }
            )
        else:
            # Return 500 to enable Cloud Tasks retry. The traceback stays out
            # of the response: Cloud Tasks does not keep the body, and anyone
            # who can reach the endpoint would read it. It is logged instead,
            # with the ERROR record of the django.tasks logger.
            return JsonResponse(
                {
                    "status": "failed",
                    "task_id": task_result.id,
                    "errors": [
                        {"exception": err.exception_class_path}
                        for err in task_result.errors
                    ],
                },
                status=500,
            )
