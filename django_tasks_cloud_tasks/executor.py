"""Task execution logic."""

import logging
from traceback import format_exception

from django.utils import timezone
from django.utils.module_loading import import_string

from django.tasks.base import TaskContext, TaskError, TaskResult, TaskResultStatus
from django.tasks.signals import task_finished, task_started

# Logger with naming convention similar to django-database-task
# Allows distinguishing log sources when using multiple backends
logger = logging.getLogger("django_tasks_cloud_tasks")


def execute_task_from_payload(payload, worker_id):
    """
    Execute task from payload.

    Args:
        payload: Payload received from Cloud Tasks (dict)
        worker_id: Worker identifier

    Returns:
        tuple: (TaskResult, success: bool)
    """
    from .backends import CloudTasksBackend

    task_id = payload["task_id"]
    task_path = payload["task_path"]
    args = payload["args"]
    kwargs = payload["kwargs"]
    queue_name = payload["queue_name"]
    backend_alias = payload["backend"]
    priority = payload.get("priority", 0)
    takes_context = payload.get("takes_context", False)
    enqueued_at_str = payload.get("enqueued_at")

    # Get task function
    task_func = import_string(task_path)

    # Parse enqueued_at
    enqueued_at = None
    if enqueued_at_str:
        from datetime import datetime

        enqueued_at = datetime.fromisoformat(enqueued_at_str)

    now = timezone.now()

    # Build TaskResult
    task_result = TaskResult(
        task=task_func,
        id=task_id,
        status=TaskResultStatus.RUNNING,
        enqueued_at=enqueued_at,
        started_at=now,
        finished_at=None,
        last_attempted_at=now,
        args=args,
        kwargs=kwargs,
        backend=backend_alias,
        errors=[],
        worker_ids=[worker_id],
    )

    # Send task_started signal
    task_started.send(sender=CloudTasksBackend, task_result=task_result)

    try:
        # Execute task
        if takes_context:
            result = task_func.call(TaskContext(task_result=task_result), *args, **kwargs)
        else:
            result = task_func.call(*args, **kwargs)

        # Success
        object.__setattr__(task_result, "finished_at", timezone.now())
        object.__setattr__(task_result, "status", TaskResultStatus.SUCCESSFUL)
        object.__setattr__(task_result, "_return_value", result)

        # Log output (format similar to django-database-task)
        logger.info(
            "Task completed successfully: id=%s path=%s",
            task_result.id,
            task_path,
        )

        task_finished.send(sender=CloudTasksBackend, task_result=task_result)

        return task_result, True

    except Exception as e:
        # Failure
        object.__setattr__(task_result, "finished_at", timezone.now())
        object.__setattr__(task_result, "status", TaskResultStatus.FAILED)

        exception_type = type(e)
        error = TaskError(
            exception_class_path=f"{exception_type.__module__}.{exception_type.__qualname__}",
            traceback="".join(format_exception(e)),
        )
        task_result.errors.append(error)

        # Log output (format similar to django-database-task)
        logger.error(
            "Task failed: id=%s path=%s error=%s",
            task_result.id,
            task_path,
            error.exception_class_path,
        )

        task_finished.send(sender=CloudTasksBackend, task_result=task_result)

        return task_result, False
