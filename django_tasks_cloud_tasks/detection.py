"""Auto-detection for GCP environments (App Engine, Cloud Run)."""

import os
import urllib.error
import urllib.request

METADATA_SERVER = "http://metadata.google.internal"
METADATA_HEADERS = {"Metadata-Flavor": "Google"}
METADATA_TIMEOUT = 2  # seconds


def is_cloud_run():
    """Check if running in Cloud Run environment."""
    return os.environ.get("K_SERVICE") is not None


def is_app_engine():
    """Check if running in App Engine environment."""
    return os.environ.get("GAE_APPLICATION") is not None


def detect_gcp_project():
    """
    Detect GCP project ID.

    Priority:
    1. GOOGLE_CLOUD_PROJECT environment variable
    2. GAE_APPLICATION environment variable (App Engine)
    3. Metadata server
    """
    # Get from environment variable
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        return project

    # App Engine case
    gae_app = os.environ.get("GAE_APPLICATION")
    if gae_app:
        # GAE_APPLICATION format is "region~project-id"
        return gae_app.split("~")[-1]

    # Get from metadata server
    return _get_metadata("project/project-id")


def detect_gcp_location():
    """
    Detect GCP location.

    Priority:
    1. CLOUD_TASKS_LOCATION environment variable (explicit)
    2. Cloud Run: CLOUD_RUN_REGION environment variable
    3. Metadata server
    """
    # Explicit environment variable
    location = os.environ.get("CLOUD_TASKS_LOCATION")
    if location:
        return location

    # Cloud Run case
    if is_cloud_run():
        region = os.environ.get("CLOUD_RUN_REGION")
        if region:
            return region

    # Get from metadata server
    zone = _get_metadata("instance/zone")
    if zone:
        # Zone format is "projects/PROJECT_NUM/zones/REGION-ZONE"
        # Extract REGION part (e.g., asia-northeast1-a -> asia-northeast1)
        zone_name = zone.split("/")[-1]
        return "-".join(zone_name.split("-")[:-1])

    return None


def detect_default_service_account():
    """Detect default service account email address."""
    return _get_metadata("instance/service-accounts/default/email")


def detect_task_handler_host():
    """
    Detect task handler host URL.

    Priority:
    1. SERVICE_URL environment variable (explicit)
    2. Cloud Run: Generate URL from K_SERVICE
    3. App Engine: Generate URL from GAE_VERSION

    Supports Blue/Green deployment.
    """
    # Explicit environment variable
    service_url = os.environ.get("SERVICE_URL")
    if service_url:
        return service_url

    if is_cloud_run():
        service = os.environ.get("K_SERVICE")
        revision = os.environ.get("K_REVISION")
        project = detect_gcp_project()
        region = os.environ.get("CLOUD_RUN_REGION")

        if all([service, project, region]):
            # Generate revision-specific URL (Blue/Green support)
            if revision:
                return f"https://{revision}---{service}-{project}.{region}.run.app"
            return f"https://{service}-{project}.{region}.run.app"

    if is_app_engine():
        version = os.environ.get("GAE_VERSION")
        project = detect_gcp_project()

        if version and project:
            # Generate version-specific URL
            return f"https://{version}-dot-{project}.appspot.com"

    return None


def _get_metadata(path):
    """Fetch data from metadata server."""
    url = f"{METADATA_SERVER}/computeMetadata/v1/{path}"
    request = urllib.request.Request(url, headers=METADATA_HEADERS)

    try:
        with urllib.request.urlopen(request, timeout=METADATA_TIMEOUT) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None
