# Django Tasks Cloud Tasks Sample Project

This directory contains a sample project for testing `django-tasks-cloud-tasks`.

## Prerequisites

- Python 3.12 or later
- Django 6.0 or later
- Docker, to run the Cloud Tasks emulator locally, or a GCP project
- Google Cloud SDK (gcloud command), to deploy to GCP

## Setup

### 1. Create virtual environment and install packages

```bash
cd examples/sample_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
# venv\Scripts\activate  # Windows

# Install packages
pip install Django>=6.0 google-cloud-tasks google-auth

# Install django-tasks-cloud-tasks (development mode)
pip install -e ../..
```

### 2. Initialize database

```bash
python manage.py migrate
```

## Running the Demo

### Start Django server

```bash
cd examples/sample_project

export GOOGLE_CLOUD_PROJECT="your-project-id"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://localhost:8000"

python manage.py runserver
```

Open http://localhost:8000/ in your browser to see the demo page with task enqueue forms.

## Local testing (without emulator)

### Without Cloud Tasks emulator

If you don't use the Cloud Tasks emulator, task enqueueing is performed against GCP,
but you can manually simulate the task execution HTTP requests.

#### 1. Start Django server

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://localhost:8000"

python manage.py runserver
```

#### 2. Simulate task execution

In another terminal, simulate the request that Cloud Tasks sends to the endpoint:

```bash
# Simulate addition task execution
curl -X POST http://localhost:8000/cloudtasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-task-001",
    "task_path": "sample_app.tasks.add_numbers",
    "args": [5, 3],
    "kwargs": {},
    "queue_name": "default",
    "backend": "default",
    "priority": 0,
    "takes_context": false,
    "enqueued_at": "2024-01-01T00:00:00+00:00"
  }'
```

Example response:
```json
{"status": "success", "task_id": "test-task-001"}
```

#### 3. Test other tasks

```bash
# Notification task
curl -X POST http://localhost:8000/cloudtasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-notify-001",
    "task_path": "sample_app.tasks.send_notification",
    "args": ["user-123", "Hello!"],
    "kwargs": {},
    "queue_name": "default",
    "backend": "default",
    "priority": 0,
    "takes_context": false,
    "enqueued_at": "2024-01-01T00:00:00+00:00"
  }'

# Task with context
curl -X POST http://localhost:8000/cloudtasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-context-001",
    "task_path": "sample_app.tasks.task_with_context",
    "args": ["Hello with context!"],
    "kwargs": {},
    "queue_name": "default",
    "backend": "default",
    "priority": 0,
    "takes_context": true,
    "enqueued_at": "2024-01-01T00:00:00+00:00"
  }'
```

## Testing with Cloud Tasks emulator

Google does not ship a Cloud Tasks emulator.
[aertje/cloud-tasks-emulator](https://github.com/aertje/cloud-tasks-emulator)
is a community one, not affiliated with Google, that implements the Cloud
Tasks v2 API and dispatches HTTP tasks the way Cloud Tasks does. With
`CLOUD_TASKS_EMULATOR_HOST` set, the backend creates its tasks there instead
of in Google Cloud, over a plaintext connection and without credentials, and
logs `Using the Cloud Tasks emulator at ...` when it connects.

### 1. Start the emulator with the sample project's queues

```bash
docker run --rm -p 8123:8123 --add-host=host.docker.internal:host-gateway \
  ghcr.io/aertje/cloud-tasks-emulator:latest \
  -host 0.0.0.0 -port 8123 \
  -initial-queue projects/sample-project/locations/asia-northeast1/queues/default \
  -initial-queue projects/sample-project/locations/asia-northeast1/queues/high-priority
```

### 2. Point the sample project at the emulator and start Django

In another terminal:

```bash
cd examples/sample_project

export CLOUD_TASKS_EMULATOR_HOST=localhost:8123
export GOOGLE_CLOUD_PROJECT="sample-project"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://host.docker.internal:8000"

python manage.py runserver 0.0.0.0:8000
```

The sample project's `ALLOWED_HOSTS` is `["*"]`, so it accepts the requests
the emulator sends to `host.docker.internal`.

### 3. Enqueue tasks via Web UI

Open http://localhost:8000/ in your browser and use the forms to enqueue
tasks. The emulator calls `/cloudtasks/execute/` for each of them, and the
Django server's console shows the request; the failing task is retried with
the emulator's default retry settings.

- The emulator runs in a container, so it reaches the Django server on the
  host as `host.docker.internal`. `--add-host` makes that name work on Linux;
  Docker Desktop provides it already. Django has to listen on `0.0.0.0` and
  accept that host name in `ALLOWED_HOSTS`.
- Queues are created when the emulator starts, one `-initial-queue` per
  queue, named after the project and location the backend uses.
- Leave `OIDC_SERVICE_ACCOUNT_EMAIL` unset. The emulator signs its OIDC
  tokens with its own key, which the endpoint does not accept, so with it
  set every task is refused with `401`. Without it the endpoint does not
  check tokens, which is what local development needs.

## Deployment to GCP (Cloud Run)

### 1. Create Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", ":8080", "sample_project.wsgi:application"]
```

### 2. Create requirements.txt

```
Django>=6.0
gunicorn
google-cloud-tasks>=2.0.0
google-auth>=2.0.0
django-tasks-cloud-tasks
```

### 3. Deploy to Cloud Run

```bash
# Build image and deploy
gcloud run deploy sample-project \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated

# Create Cloud Tasks queues
gcloud tasks queues create default \
  --location asia-northeast1

gcloud tasks queues create high-priority \
  --location asia-northeast1
```

### 4. Set environment variables

Set the following environment variables in Cloud Run:

- `GOOGLE_CLOUD_PROJECT`: GCP project ID (auto-detected)
- `CLOUD_TASKS_LOCATION`: Cloud Tasks location (auto-detected)
- `SERVICE_URL`: Cloud Run URL (auto-detected)
- `CLOUD_TASKS_OIDC_AUDIENCE`: OIDC authentication audience (set in production)

## Web UI Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Demo page with task enqueue forms |
| `/enqueue/add/` | POST | Enqueue addition task |
| `/enqueue/notify/` | POST | Enqueue notification task |
| `/enqueue/process/` | POST | Enqueue data processing task |
| `/enqueue/urgent/` | POST | Enqueue high-priority task |
| `/enqueue/context/` | POST | Enqueue task with context |
| `/enqueue/failing/` | POST | Enqueue task that always fails (for retry testing) |
| `/cloudtasks/execute/` | POST | Task execution endpoint from Cloud Tasks |

## Troubleshooting

### "CLOUD_TASKS_PROJECT is required" error

Set the environment variable `GOOGLE_CLOUD_PROJECT`:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

### "CLOUD_TASKS_LOCATION is required" error

Set the environment variable `CLOUD_TASKS_LOCATION`:

```bash
export CLOUD_TASKS_LOCATION="asia-northeast1"
```

### "TASK_HANDLER_HOST is required" error

Set the environment variable `SERVICE_URL`:

```bash
export SERVICE_URL="http://localhost:8000"
```

### Cannot connect to Cloud Tasks emulator

Make sure the emulator is running and set the environment variable:

```bash
export CLOUD_TASKS_EMULATOR_HOST=localhost:8123
```

If tasks are created but never reach Django, the emulator cannot reach
`SERVICE_URL`: from inside its container `localhost` is the container
itself, so use `http://host.docker.internal:8000` and run Django on
`0.0.0.0:8000`.
