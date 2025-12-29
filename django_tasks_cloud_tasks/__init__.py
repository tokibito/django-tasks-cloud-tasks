"""
Django Tasks Cloud Tasks Backend

A backend for Django 6.0 task framework using Cloud Tasks.
Task parameters are stored in Cloud Tasks payload, not in database.
"""

__version__ = "0.1.0"

# Detection utilities are always available (no external dependencies)
from .detection import (
    detect_gcp_project,
    detect_gcp_location,
    detect_task_handler_host,
    detect_default_service_account,
    is_cloud_run,
    is_app_engine,
)

__all__ = [
    # Version
    "__version__",
    # Detection utilities
    "detect_gcp_project",
    "detect_gcp_location",
    "detect_task_handler_host",
    "detect_default_service_account",
    "is_cloud_run",
    "is_app_engine",
    # Lazy imports below
    "CloudTasksBackend",
    "create_oidc_auth_handler",
    "verify_cloud_tasks_oidc",
]


def __getattr__(name):
    """Lazy import - modules requiring google-cloud-tasks are loaded only when needed."""
    if name == "CloudTasksBackend":
        from .backends import CloudTasksBackend

        return CloudTasksBackend
    if name == "create_oidc_auth_handler":
        from .auth import create_oidc_auth_handler

        return create_oidc_auth_handler
    if name == "verify_cloud_tasks_oidc":
        from .auth import verify_cloud_tasks_oidc

        return verify_cloud_tasks_oidc
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
