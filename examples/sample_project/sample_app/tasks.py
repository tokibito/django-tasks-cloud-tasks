"""
Sample task definitions.

Examples of tasks executed by the Cloud Tasks backend.
"""

import logging
import time

from django.tasks import task

logger = logging.getLogger(__name__)


@task
def add_numbers(x, y):
    """
    Simple task to add two numbers.

    Args:
        x: First number
        y: Second number

    Returns:
        Sum of the two numbers
    """
    logger.info(f"Adding numbers: {x} + {y}")
    result = x + y
    logger.info(f"Result: {result}")
    return result


@task
def send_notification(user_id, message):
    """
    Task to send notification (simulation).

    Args:
        user_id: User ID
        message: Notification message
    """
    logger.info(f"Sending notification to user {user_id}: {message}")
    # Implement actual notification sending here
    time.sleep(1)  # Simulate sending
    logger.info(f"Notification sent to user {user_id}")
    return {"status": "sent", "user_id": user_id}


@task
def process_data(data_id, options=None):
    """
    Data processing task.

    Args:
        data_id: ID of data to process
        options: Processing options (dict)
    """
    options = options or {}
    logger.info(f"Processing data {data_id} with options: {options}")
    # Simulate data processing
    time.sleep(2)
    logger.info(f"Data {data_id} processed successfully")
    return {"data_id": data_id, "processed": True}


@task(queue_name="high-priority")
def urgent_task(task_name):
    """
    Task executed in high-priority queue.

    Args:
        task_name: Task name
    """
    logger.info(f"Executing urgent task: {task_name}")
    return {"task": task_name, "priority": "high"}


@task(takes_context=True)
def task_with_context(context, message):
    """
    Task using context information.

    Args:
        context: Task context
        message: Message
    """
    task_id = context.task_result.id
    attempt = context.attempt
    logger.info(f"Task {task_id} (attempt {attempt}): {message}")
    return {
        "task_id": task_id,
        "attempt": attempt,
        "message": message,
    }


@task
def failing_task():
    """
    Task that intentionally fails (for retry testing).
    """
    logger.error("This task always fails!")
    raise ValueError("Intentional failure for testing")
