# django-tasks-cloud-tasks

[![CI](https://github.com/tokibito/django-tasks-cloud-tasks/actions/workflows/ci.yml/badge.svg)](https://github.com/tokibito/django-tasks-cloud-tasks/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/django-tasks-cloud-tasks.svg)](https://badge.fury.io/py/django-tasks-cloud-tasks)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-tasks-cloud-tasks.svg)](https://pypi.org/project/django-tasks-cloud-tasks/)
[![Django Versions](https://img.shields.io/badge/django-6.0%20%7C%206.1-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Google Cloud Tasks backend for Django 6.0's built-in task framework.

## Features

- **Cloud Tasks integration** - Enqueue tasks to Google Cloud Tasks
- **HTTP callback execution** - Tasks are executed via HTTP POST requests from Cloud Tasks
- **OIDC authentication** - Secure task execution with OIDC token verification
- **Auto-detection** - Automatically detects GCP project, location, and service URL on Cloud Run/App Engine
- **Delayed execution** - Schedule tasks to run at a specific time with `run_after`
- **Task context** - Access task metadata via context

## Architecture

```mermaid
sequenceDiagram
    participant App as Application
    participant Backend as CloudTasksBackend
    participant CT as Cloud Tasks
    participant Handler as /cloudtasks/execute/

    Note over App,Handler: Task Enqueue
    App->>Backend: task.enqueue(args, kwargs)
    Backend->>Backend: Serialize task data
    Backend->>CT: Create HTTP Task (with payload)
    CT-->>Backend: Task name
    Backend-->>App: TaskResult (id, status=READY)

    Note over App,Handler: Task Execution (triggered by Cloud Tasks)
    CT->>Handler: POST /cloudtasks/execute/<br/>(with OIDC token if configured)
    Handler->>Handler: Verify OIDC token (optional)
    Handler->>Handler: Deserialize task data
    Handler->>Handler: Execute task function
    alt Success
        Handler-->>CT: HTTP 200
    else Failure
        Handler-->>CT: HTTP 500 (triggers retry)
    end
```

## Requirements

- Python 3.12+
- Django 6.0+

google-cloud-tasks and google-auth (for OIDC verification) are dependencies
of the package and are installed with it.

## Installation

```bash
pip install django-tasks-cloud-tasks
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ...
    "django_tasks_cloud_tasks",
]
```

### 2. Configure the task backend

**On Cloud Run / App Engine**, all settings are auto-detected from the environment. You only need:

```python
TASKS = {
    "default": {
        "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
        "QUEUES": [],  # Empty list allows all queue names
    },
}
```

> **Note:** On GCP environments (Cloud Run, App Engine, GCE), the following are automatically detected:
> - **Project ID**: from `GOOGLE_CLOUD_PROJECT` env var or GCP metadata server
> - **Location**: from `CLOUD_TASKS_LOCATION`, `CLOUD_RUN_REGION` env var, or metadata server
> - **Service URL**: from `SERVICE_URL` env var, or generated from `K_SERVICE` (Cloud Run) / `GAE_SERVICE` (App Engine)
> - **Service Account**: from metadata server (for OIDC authentication)
>
> **About Service Accounts:** On GCP, applications run with a **runtime service account** (not API keys or JSON key files). Cloud Run, App Engine, and GCE automatically provide credentials via the metadata server. You don't need to create or download any key files.
>
> Simply grant the `roles/cloudtasks.enqueuer` role to your runtime service account:
> ```bash
> # For Cloud Run (uses Compute Engine default service account by default)
> gcloud projects add-iam-policy-binding PROJECT_ID \
>     --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
>     --role="roles/cloudtasks.enqueuer"
> ```
> The backend will automatically use these credentials for both creating tasks and OIDC authentication.

**For local development**, set environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://localhost:8000"
```

With these environment variables set, the same minimal configuration works:

```python
TASKS = {
    "default": {
        "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
        "QUEUES": [],
    },
}
```

Or configure explicitly in settings:

```python
TASKS = {
    "default": {
        "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
        "QUEUES": [],
        "OPTIONS": {
            "CLOUD_TASKS_PROJECT": "your-project-id",
            "CLOUD_TASKS_LOCATION": "asia-northeast1",
            "TASK_HANDLER_HOST": "http://localhost:8000",
        },
    },
}
```

### 3. Add URL configuration

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path("cloudtasks/", include("django_tasks_cloud_tasks.urls")),
]
```

### 4. Define a task

```python
from django.tasks import task


@task
def send_welcome_email(user_id):
    user = User.objects.get(id=user_id)
    # Send email...
    return f"Email sent to {user.email}"
```

### 5. Enqueue the task

```python
result = send_welcome_email.enqueue(user_id=123)
print(f"Task ID: {result.id}")
```

### 6. Create Cloud Tasks queue

```bash
gcloud tasks queues create default --location=asia-northeast1
```

## Usage

### Important: JSON-Serializable Parameters

Task arguments, keyword arguments, and return values **must be JSON-serializable**.

Supported types:
- `str`, `int`, `float`, `bool`, `None`
- `dict` (with JSON-serializable keys and values)
- `list`, `tuple` (with JSON-serializable elements)

**Not supported** (will raise `TypeError`):
- `datetime`, `date`, `time` - convert to ISO string: `dt.isoformat()`
- `UUID` - convert to string: `str(uuid)`
- `Decimal` - convert to float or string
- Custom objects - serialize manually

```python
from django.tasks import task


# ❌ This will raise TypeError
@task
def bad_task(user_id, created_at):
    pass


bad_task.enqueue(123, datetime.now())  # TypeError!


# ✅ Convert to JSON-serializable types
@task
def good_task(user_id, created_at_iso):
    created_at = datetime.fromisoformat(created_at_iso)
    # ...


good_task.enqueue(123, datetime.now().isoformat())  # OK
```

### Priority

Task priority is not supported: Cloud Tasks dispatches a queue in order of
schedule time and has no priority, so a task that sets `priority` raises
`InvalidTask` when it is defined. Put urgent work on its own queue instead,
as in [Queue-specific tasks](#queue-specific-tasks).

### Delayed execution

```python
from datetime import timedelta
from django.utils import timezone

# Run 1 hour from now
delayed_task = my_task.using(run_after=timezone.now() + timedelta(hours=1))
result = delayed_task.enqueue()
```

### Task with context

```python
@task(takes_context=True)
def task_with_context(context, message):
    task_id = context.task_result.id
    attempt = context.attempt
    return f"Task {task_id} (attempt {attempt}): {message}"
```

### Queue-specific tasks

```python
@task(queue_name="high-priority")
def urgent_notification():
    pass


# Create the queue in Cloud Tasks
# gcloud tasks queues create high-priority --location=asia-northeast1
```

## Configuration Options

```python
TASKS = {
    "default": {
        "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
        "QUEUES": [],  # Empty list allows all queue names
        "OPTIONS": {
            # Auto-detected on Cloud Run / App Engine, or set explicitly
            "CLOUD_TASKS_PROJECT": "your-project-id",
            "CLOUD_TASKS_LOCATION": "asia-northeast1",
            "TASK_HANDLER_HOST": "https://your-app.run.app",
            "TASK_HANDLER_PATH": "/cloudtasks/execute/",  # default
            # OIDC authentication (the service account is auto-detected on GCP)
            "OIDC_SERVICE_ACCOUNT_EMAIL": "cloud-tasks-invoker@your-project.iam.gserviceaccount.com",
            "OIDC_AUDIENCE": "https://your-app.run.app",
        },
    },
}
```

### Configuration Reference

| Option | Required | Description |
|--------|----------|-------------|
| `CLOUD_TASKS_PROJECT` | Auto-detected | GCP project ID |
| `CLOUD_TASKS_LOCATION` | Auto-detected | Cloud Tasks location (e.g., `asia-northeast1`) |
| `TASK_HANDLER_HOST` | Auto-detected | Base URL for task execution endpoint |
| `TASK_HANDLER_PATH` | No | Task execution endpoint path (default: `/cloudtasks/execute/`) |
| `OIDC_SERVICE_ACCOUNT_EMAIL` | Auto-detected | Service account Cloud Tasks signs an OIDC token as. When set or detected, the endpoint verifies the token (see [OIDC Authentication](#oidc-authentication)) |
| `OIDC_AUDIENCE` | No | Audience of the OIDC token, both sent and verified (defaults to `TASK_HANDLER_HOST`) |

### Auto-Detection

Settings are automatically detected from environment variables or GCP metadata:

| Setting | Detection Source |
|---------|------------------|
| `CLOUD_TASKS_PROJECT` | `GOOGLE_CLOUD_PROJECT` env var, or metadata server |
| `CLOUD_TASKS_LOCATION` | `CLOUD_TASKS_LOCATION`, `CLOUD_RUN_REGION` env var, or metadata server |
| `TASK_HANDLER_HOST` | `SERVICE_URL` env var, or built from `K_SERVICE` (Cloud Run) / `GAE_SERVICE` (App Engine) |
| `OIDC_SERVICE_ACCOUNT_EMAIL` | The default service account, from the metadata server |

### Environment Variables

For local development:

| Environment Variable | Description |
|---------------------|-------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `CLOUD_TASKS_LOCATION` | Cloud Tasks location |
| `SERVICE_URL` | Task execution endpoint URL |
| `CLOUD_TASKS_EMULATOR_HOST` | Cloud Tasks emulator host (for local development) |

## HTTP Endpoint

### POST `/cloudtasks/execute/`

Task execution endpoint called by Cloud Tasks. It runs the task the request
names with the arguments the request gives, so it has to be authenticated;
see [OIDC Authentication](#oidc-authentication).

Request body (JSON):
```json
{
  "task_id": "uuid",
  "task_path": "myapp.tasks.send_email",
  "args": [1, 2, 3],
  "kwargs": {"key": "value"},
  "queue_name": "default",
  "backend": "default",
  "priority": 0,
  "takes_context": false,
  "enqueued_at": "2024-01-01T00:00:00+00:00"
}
```

Response (success):
```json
{"status": "success", "task_id": "uuid"}
```

Response (the task raised an exception), with status `500` so that Cloud
Tasks retries the task:
```json
{"status": "failed", "task_id": "uuid", "errors": [{"exception": "builtins.ValueError"}]}
```

The traceback is not in the response. It is in the log, under the task id;
see [Logging](#logging).

Response (the payload cannot be executed: a required field is missing or
has the wrong type, or the body is not a JSON object), with status `400`:
```json
{"error": "Invalid payload", "detail": "missing field: task_path"}
```

The required fields are `task_id`, `task_path`, `args`, `kwargs`,
`queue_name` and `backend`. Cloud Tasks retries a `400` like any answer
outside 2xx, so a payload enqueued by another version of the application
during a deploy can still be picked up by a revision that understands it.
The log names the cause; see [Logging](#logging).

## OIDC Authentication

Cloud Tasks can sign each request with an OIDC token for a service account,
and the endpoint verifies it. Both sides are driven by the backend's
options:

- With `OIDC_SERVICE_ACCOUNT_EMAIL` set, or detected from the metadata
  server on Cloud Run and App Engine, the backend asks Cloud Tasks to send a
  token, and the endpoint rejects a request without a valid one with
  `401 Unauthorized`.
- The token's audience is `OIDC_AUDIENCE`, which defaults to
  `TASK_HANDLER_HOST`. The endpoint checks the same value, so the two cannot
  drift apart.

**Without a service account, the endpoint is open**: anyone who can reach it
can run any task with any arguments. That is the case outside Google Cloud,
for example in local development, where the metadata server is not
available. A deployment that runs without OIDC has to protect the endpoint
some other way.

The endpoint uses the OIDC options of the `default` task backend. A project
whose Cloud Tasks backend has another alias says so in its URLconf:

```python
from django.urls import path

from django_tasks_cloud_tasks.views import ExecuteTaskView

urlpatterns = [
    path(
        "cloudtasks/execute/",
        ExecuteTaskView.as_view(backend_alias="cloud"),
    ),
]
```

The `CLOUD_TASKS_OIDC_AUDIENCE` Django setting, when set, turns verification
on with that audience whatever the backend says. It is kept for projects
that used it before the backend's options were read; new projects do not
need it.

### Setup

1. Create a service account for OIDC:
   ```bash
   gcloud iam service-accounts create cloud-tasks-invoker \
       --display-name="Cloud Tasks Invoker"
   ```

2. Grant required roles:
   ```bash
   # Allow your service to create Cloud Tasks
   gcloud projects add-iam-policy-binding PROJECT_ID \
       --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
       --role="roles/cloudtasks.enqueuer"

   # Allow impersonation for OIDC
   gcloud iam service-accounts add-iam-policy-binding \
       cloud-tasks-invoker@PROJECT_ID.iam.gserviceaccount.com \
       --member="serviceAccount:PROJECT_ID@appspot.gserviceaccount.com" \
       --role="roles/iam.serviceAccountUser"
   ```

3. Configure the backend:
   ```python
   TASKS = {
       "default": {
           "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
           "QUEUES": [],  # Empty list allows all queue names
           "OPTIONS": {
               # CLOUD_TASKS_PROJECT, CLOUD_TASKS_LOCATION, TASK_HANDLER_HOST are auto-detected on Cloud Run
               "OIDC_SERVICE_ACCOUNT_EMAIL": "cloud-tasks-invoker@PROJECT_ID.iam.gserviceaccount.com",
           },
       },
   }
   ```

4. Check that a request without a token is refused:
   ```bash
   curl -i -X POST https://your-app.run.app/cloudtasks/execute/ \
       -H "Content-Type: application/json" -d '{}'
   ```
   ```
   HTTP/2 401
   ...
   {"error": "Unauthorized", "detail": "Missing or invalid Authorization header"}
   ```

## Logging

The package logs to the `django_tasks_cloud_tasks` logger: a task that
completes at `INFO`, a task that fails and a token that fails OIDC
verification at `ERROR`, and a request the endpoint refuses at `WARNING`.

A payload the endpoint cannot execute is logged at `ERROR` with what is
wrong, the task it names as far as it can be read, the keys it has (not
their values, which may hold the task's arguments), and the Cloud Tasks
headers. Without those headers the request did not come from Cloud Tasks;
`retry_count` says how often Cloud Tasks has already tried it:

```
Invalid payload: detail=args must be a list id=3kZ... path=myapp.tasks.send_email keys=['args', 'backend', ...] queue=default cloud_task=4385939532263547437 retry_count=2
```

The traceback of a failed task is in a record of Django's own
`django.tasks` logger: `Task id=... path=... state=FAILED`, at `ERROR`, with
the exception attached. Django's default logging configuration prints the
`django` loggers to the console only when `DEBUG` is on, so in production
that record is dropped unless a handler is attached to it.

When neither the `django_tasks_cloud_tasks` logger nor the root logger has a
handler, Python prints `WARNING` and above to stderr and drops the rest. To
see every record, including the tracebacks, attach a handler to both
loggers in `LOGGING`:

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django_tasks_cloud_tasks": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.tasks": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

On Cloud Run and App Engine, stderr goes to Cloud Logging.

## Local Development

### Without Cloud Tasks Emulator

You can manually simulate task execution:

```bash
# Start Django server
export GOOGLE_CLOUD_PROJECT="your-project-id"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://localhost:8000"
python manage.py runserver

# Simulate task execution
curl -X POST http://localhost:8000/cloudtasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-task-001",
    "task_path": "myapp.tasks.add_numbers",
    "args": [5, 3],
    "kwargs": {},
    "queue_name": "default",
    "backend": "default",
    "priority": 0,
    "takes_context": false,
    "enqueued_at": "2024-01-01T00:00:00+00:00"
  }'
```

### With Cloud Tasks Emulator

```bash
# Start Cloud Tasks emulator
gcloud beta emulators tasks start --host-port=localhost:8123

# Set environment variables
export CLOUD_TASKS_EMULATOR_HOST=localhost:8123
export GOOGLE_CLOUD_PROJECT="sample-project"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://localhost:8000"

# Create queues
gcloud tasks queues create default --location=asia-northeast1 --project=sample-project

# Start Django server
python manage.py runserver
```

## Deployment to Cloud Run

### 1. Create Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", ":8080", "myproject.wsgi:application"]
```

### 2. Deploy

```bash
# Deploy to Cloud Run
gcloud run deploy myapp \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated

# Create Cloud Tasks queues
gcloud tasks queues create default --location asia-northeast1
gcloud tasks queues create high-priority --location asia-northeast1
```

### 3. Configuration

All settings are auto-detected on Cloud Run. No additional configuration needed for basic usage.

`--allow-unauthenticated` lets Cloud Tasks reach the service without IAM.
The task endpoint is still protected: the service account is detected from
the metadata server, so Cloud Tasks sends an OIDC token and the endpoint
verifies it (see [OIDC Authentication](#oidc-authentication)).

## Example Project

See the [examples/](examples/) directory for a complete sample project with a web UI for testing task enqueueing.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for how to set up a development environment and what a pull request needs.

## License

MIT License
