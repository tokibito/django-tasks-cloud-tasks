# Django Tasks Cloud Tasks Sample Project

This directory contains a sample project for testing `django-tasks-cloud-tasks`.

## Prerequisites

- Python 3.12 or later
- Django 6.0 or later
- Google Cloud SDK (gcloud command)
- Cloud Tasks emulator (for local testing) or GCP project

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
curl -X POST http://localhost:8000/tasks/execute/ \
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
curl -X POST http://localhost:8000/tasks/execute/ \
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
curl -X POST http://localhost:8000/tasks/execute/ \
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

### 1. Install and start Cloud Tasks emulator

```bash
# Install gcloud component (first time only)
gcloud components install cloud-tasks-emulator

# Start emulator
gcloud beta emulators tasks start --host-port=localhost:8123
```

### 2. Set environment variables for emulator

In another terminal:

```bash
# Environment variables to connect to emulator
export CLOUD_TASKS_EMULATOR_HOST=localhost:8123
export GOOGLE_CLOUD_PROJECT="sample-project"
export CLOUD_TASKS_LOCATION="asia-northeast1"
export SERVICE_URL="http://localhost:8000"
```

### 3. Create Cloud Tasks queues

```bash
# Create queues with gcloud (against emulator)
gcloud tasks queues create default \
  --location=asia-northeast1 \
  --project=sample-project

gcloud tasks queues create high-priority \
  --location=asia-northeast1 \
  --project=sample-project
```

### 4. Start Django server

```bash
python manage.py runserver
```

### 5. Enqueue tasks via Web UI

Open http://localhost:8000/ in your browser and use the forms to enqueue tasks.

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
| `/tasks/execute/` | POST | Task execution endpoint from Cloud Tasks |

## Troubleshooting

### "PROJECT_ID is required" error

Set the environment variable `GOOGLE_CLOUD_PROJECT`:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

### "LOCATION is required" error

Set the environment variable `CLOUD_TASKS_LOCATION`:

```bash
export CLOUD_TASKS_LOCATION="asia-northeast1"
```

### "SERVICE_URL is required" error

Set the environment variable `SERVICE_URL`:

```bash
export SERVICE_URL="http://localhost:8000"
```

### Cannot connect to Cloud Tasks emulator

Make sure the emulator is running and set the environment variable:

```bash
export CLOUD_TASKS_EMULATOR_HOST=localhost:8123
```
