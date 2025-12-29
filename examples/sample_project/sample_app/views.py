"""
Sample views.

Views for enqueueing tasks with HTML templates.
"""

import json

from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .tasks import (
    add_numbers,
    send_notification,
    process_data,
    urgent_task,
    task_with_context,
    failing_task,
)


class IndexView(View):
    """Index page with task enqueue forms."""

    def get(self, request):
        return render(request, "sample_app/index.html")


class EnqueueAddView(View):
    """Enqueue addition task."""

    def post(self, request):
        x = int(request.POST.get("x", 1))
        y = int(request.POST.get("y", 2))

        result = add_numbers.enqueue(x, y)

        return render(
            request,
            "sample_app/result.html",
            {
                "task_id": result.id,
                "task_path": "sample_app.tasks.add_numbers",
                "args": json.dumps(result.args),
                "kwargs": json.dumps(result.kwargs),
                "queue_name": "default",
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class EnqueueNotifyView(View):
    """Enqueue notification task."""

    def post(self, request):
        user_id = request.POST.get("user_id", "user-123")
        message = request.POST.get("message", "Hello from Cloud Tasks!")

        result = send_notification.enqueue(user_id, message)

        return render(
            request,
            "sample_app/result.html",
            {
                "task_id": result.id,
                "task_path": "sample_app.tasks.send_notification",
                "args": json.dumps(result.args),
                "kwargs": json.dumps(result.kwargs),
                "queue_name": "default",
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class EnqueueProcessView(View):
    """Enqueue data processing task."""

    def post(self, request):
        data_id = request.POST.get("data_id", "data-001")
        options = {"format": "json", "compress": True}

        result = process_data.enqueue(data_id, options=options)

        return render(
            request,
            "sample_app/result.html",
            {
                "task_id": result.id,
                "task_path": "sample_app.tasks.process_data",
                "args": json.dumps(result.args),
                "kwargs": json.dumps(result.kwargs),
                "queue_name": "default",
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class EnqueueUrgentView(View):
    """Enqueue high-priority task."""

    def post(self, request):
        task_name = request.POST.get("task_name", "important-job")

        result = urgent_task.enqueue(task_name)

        return render(
            request,
            "sample_app/result.html",
            {
                "task_id": result.id,
                "task_path": "sample_app.tasks.urgent_task",
                "args": json.dumps(result.args),
                "kwargs": json.dumps(result.kwargs),
                "queue_name": "high-priority",
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class EnqueueContextView(View):
    """Enqueue task with context."""

    def post(self, request):
        message = request.POST.get("message", "Hello with context!")

        result = task_with_context.enqueue(message)

        return render(
            request,
            "sample_app/result.html",
            {
                "task_id": result.id,
                "task_path": "sample_app.tasks.task_with_context",
                "args": json.dumps(result.args),
                "kwargs": json.dumps(result.kwargs),
                "queue_name": "default",
            },
        )


@method_decorator(csrf_exempt, name="dispatch")
class EnqueueFailingView(View):
    """Enqueue task that always fails (for retry testing)."""

    def post(self, request):
        result = failing_task.enqueue()

        return render(
            request,
            "sample_app/result.html",
            {
                "task_id": result.id,
                "task_path": "sample_app.tasks.failing_task",
                "args": json.dumps(result.args),
                "kwargs": json.dumps(result.kwargs),
                "queue_name": "default",
            },
        )
