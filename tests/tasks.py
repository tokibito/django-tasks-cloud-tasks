"""Task definitions for testing."""

from django.tasks import task


@task
def add_numbers(x, y):
    """Task that adds two numbers."""
    return x + y


@task
def simple_task(x):
    """Simple task that doubles input."""
    return x * 2


@task
def message_task(message, count=1):
    """Task that repeats a message."""
    return message * count


@task
def failing_task():
    """Task that always fails."""
    raise ValueError("Something went wrong")


@task
def failing_view_task():
    """Task that fails for view testing."""
    raise RuntimeError("Task failed intentionally")


@task(takes_context=True)
def task_with_context(context, message):
    """Task that receives context."""
    return f"Task {context.task_result.id}: {message}"
