"""Task execution logic."""

import logging
from traceback import format_exception

from django.tasks.base import (
    Task,
    TaskContext,
    TaskError,
    TaskResult,
    TaskResultStatus,
)
from django.tasks.signals import task_finished, task_started
from django.utils import timezone
from django.utils.module_loading import import_string

# Logger with naming convention similar to django-database-task
# Allows distinguishing log sources when using multiple backends
logger = logging.getLogger("django_tasks_cloud_tasks")

# Fields execute_task_from_payload() requires, with the JSON type of each.
PAYLOAD_FIELDS = {
    "task_id": (str, "a string"),
    "task_path": (str, "a string"),
    "args": (list, "a list"),
    "kwargs": (dict, "an object"),
    "queue_name": (str, "a string"),
    "backend": (str, "a string"),
}


def validate_payload(payload):
    """
    Check that a payload can be executed.

    Args:
        payload: Payload received from Cloud Tasks, as parsed from JSON

    Returns:
        str: Why the payload cannot be executed, or None when it can
    """
    if not isinstance(payload, dict):
        return f"the payload must be a JSON object, not {_json_type(payload)}"

    for name, (expected_type, description) in PAYLOAD_FIELDS.items():
        if name not in payload:
            return f"missing field: {name}"
        if not isinstance(payload[name], expected_type):
            return f"{name} must be {description}"

    enqueued_at = payload.get("enqueued_at")
    if enqueued_at is not None:
        from datetime import datetime

        try:
            datetime.fromisoformat(enqueued_at)
        except (TypeError, ValueError):
            return "enqueued_at must be an ISO 8601 date and time"

    return None


def cloud_tasks_log_fields(headers):
    """
    Read the Cloud Tasks request headers that identify an attempt.

    Args:
        headers: The request headers, or None outside a request

    Returns:
        tuple: (queue name, Cloud Tasks task name, retry count), each None
        when the header is absent, as on a request Cloud Tasks did not send
    """
    if headers is None:
        return None, None, None
    return (
        headers.get("X-CloudTasks-QueueName"),
        headers.get("X-CloudTasks-TaskName"),
        headers.get("X-CloudTasks-TaskRetryCount"),
    )


def _task_error(exc):
    exception_type = type(exc)
    return TaskError(
        exception_class_path=f"{exception_type.__module__}.{exception_type.__qualname__}",
        traceback="".join(format_exception(exc)),
    )


def _json_type(value):
    """Name the JSON type of a value parsed from JSON."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, int | float):
        return "a number"
    if isinstance(value, str):
        return "a string"
    return "an array"


def execute_task_from_payload(payload, worker_id, headers=None):
    """
    Execute task from payload.

    A task that cannot be resolved (the module was renamed, the function
    removed, the revision runs older code than the one that enqueued it, or
    the path names something that is not a Task) is reported as FAILED with
    the error, like a task that raised. task_started and task_finished are
    not sent for it, since there is no task to send them with; the ERROR
    record "Task could not be started" reports it instead.

    Args:
        payload: Payload received from Cloud Tasks (dict)
        worker_id: Worker identifier
        headers: The request headers, for the Cloud Tasks fields in the log

    Returns:
        tuple: (TaskResult, success: bool). The result of a task that could
        not be started has ``task`` set to None.
    """
    from .backends import CloudTasksBackend

    task_id = payload["task_id"]
    task_path = payload["task_path"]
    args = payload["args"]
    kwargs = payload["kwargs"]
    # queue_name and priority are stored in payload for potential future use
    _ = payload["queue_name"]  # noqa: F841
    backend_alias = payload["backend"]
    _ = payload.get("priority", 0)  # noqa: F841
    takes_context = payload.get("takes_context", False)
    enqueued_at_str = payload.get("enqueued_at")

    # Parse enqueued_at
    enqueued_at = None
    if enqueued_at_str:
        from datetime import datetime

        enqueued_at = datetime.fromisoformat(enqueued_at_str)

    now = timezone.now()

    # Get task function
    try:
        task_func = import_string(task_path)
        if not isinstance(task_func, Task):
            raise TypeError(f"{task_path} is not a Task")
    except Exception as e:
        error = _task_error(e)
        logger.exception(
            "Task could not be started: id=%s path=%s error=%s queue=%s "
            "cloud_task=%s retry_count=%s",
            task_id,
            task_path,
            error.exception_class_path,
            *cloud_tasks_log_fields(headers),
        )
        task_result = TaskResult(
            task=None,
            id=task_id,
            status=TaskResultStatus.FAILED,
            enqueued_at=enqueued_at,
            started_at=None,
            finished_at=now,
            last_attempted_at=now,
            args=args,
            kwargs=kwargs,
            backend=backend_alias,
            errors=[error],
            worker_ids=[worker_id],
        )
        return task_result, False

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
            result = task_func.call(
                TaskContext(task_result=task_result), *args, **kwargs
            )
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

        error = _task_error(e)
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
