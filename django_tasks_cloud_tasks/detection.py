"""Auto-detection for GCP environments (App Engine, Cloud Run)."""

import os
import urllib.error
import urllib.request
import warnings

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
    2. Cloud Run: the region of the service (CLOUD_RUN_REGION, deprecated,
       or the metadata server)
    3. Metadata server, from the zone
    """
    # Explicit environment variable
    location = os.environ.get("CLOUD_TASKS_LOCATION")
    if location:
        return location

    # Cloud Run case
    if is_cloud_run():
        region = _detect_cloud_run_region()
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
    2. Cloud Run: Generate URL from K_SERVICE, the project number and the
       region
    3. App Engine: Generate URL from GAE_VERSION and GAE_SERVICE

    On App Engine the URL names the version, so tasks run on the version
    that enqueued them. On Cloud Run it is the service URL, which serves the
    revisions that receive traffic: a URL for one revision exists only as a
    traffic tag, which the environment does not reveal, so pinning tasks to
    a revision needs a tag and SERVICE_URL.
    """
    # Explicit environment variable
    service_url = os.environ.get("SERVICE_URL")
    if service_url:
        return service_url

    if is_cloud_run():
        service = os.environ.get("K_SERVICE")
        region = _detect_cloud_run_region()
        # The deterministic Cloud Run URL carries the project number, which
        # no environment variable holds, not the project ID.
        project_number = _get_metadata("project/numeric-project-id")

        # Cloud Run gives a service this URL only when the first DNS label
        # fits in 63 characters; a longer one has a hash-based URL alone.
        if all([service, region, project_number]) and (
            len(f"{service}-{project_number}") <= 63
        ):
            # Format: https://{service}-{project-number}.{region}.run.app
            return f"https://{service}-{project_number}.{region}.run.app"

    if is_app_engine():
        service = os.environ.get("GAE_SERVICE")
        version = os.environ.get("GAE_VERSION")
        project = detect_gcp_project()

        if version and project:
            # Generate version-specific URL. A service other than the
            # default one is reached under its own name.
            if service and service != "default":
                return f"https://{version}-dot-{service}-dot-{project}.appspot.com"
            return f"https://{version}-dot-{project}.appspot.com"

    return None


def _detect_cloud_run_region():
    """
    Detect the region of the Cloud Run service.

    Cloud Run does not set CLOUD_RUN_REGION. It is still read, with a
    DeprecationWarning, for projects that set it by hand; otherwise the
    region comes from the metadata server.
    """
    region = os.environ.get("CLOUD_RUN_REGION")
    if region:
        warnings.warn(
            "The CLOUD_RUN_REGION environment variable is deprecated and will "
            "not be read from django-tasks-cloud-tasks 0.3.0. The Cloud Run "
            "region is detected from the metadata server; set "
            "CLOUD_TASKS_LOCATION for the Cloud Tasks location, or "
            "SERVICE_URL for the task handler host.",
            DeprecationWarning,
            stacklevel=3,
        )
        return region

    # Format: "projects/PROJECT_NUMBER/regions/REGION"
    region = _get_metadata("instance/region")
    if region:
        return region.split("/")[-1]
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
