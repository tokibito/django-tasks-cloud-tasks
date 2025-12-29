"""Views for receiving requests from Cloud Tasks and executing tasks."""

import json
import logging

from django.http import JsonResponse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .executor import execute_task_from_payload

logger = logging.getLogger("django_tasks_cloud_tasks")


@method_decorator(csrf_exempt, name="dispatch")
class ExecuteTaskView(View):
    """
    View for receiving requests from Cloud Tasks and executing tasks.
    """

    def get_auth_handler(self):
        """
        Get authentication handler.

        Can be overridden in subclasses.
        """
        from django.conf import settings

        audience = getattr(settings, "CLOUD_TASKS_OIDC_AUDIENCE", None)
        if audience:
            from .auth import create_oidc_auth_handler

            return create_oidc_auth_handler(audience)

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
            # Return 500 to enable Cloud Tasks retry
            return JsonResponse(
                {
                    "status": "failed",
                    "task_id": task_result.id,
                    "errors": [
                        {
                            "exception": err.exception_class_path,
                            "traceback": err.traceback,
                        }
                        for err in task_result.errors
                    ],
                },
                status=500,
            )
