"""Tests for views.py"""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, override_settings


@pytest.mark.django_db
class TestExecuteTaskView:
    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
                "QUEUES": ["default"],
                "OPTIONS": {
                    "CLOUD_TASKS_PROJECT": "test-project",
                    "CLOUD_TASKS_LOCATION": "us-central1",
                    "TASK_HANDLER_HOST": "https://test.example.com",
                },
            },
        }
    )
    def test_execute_task_success(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView
        from tests.tasks import simple_task

        factory = RequestFactory()
        payload = {
            "task_id": "view-test-task-123",
            "task_path": f"{simple_task.module_path}",
            "args": [5],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        request = factory.post(
            "/tasks/execute/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        view = ExecuteTaskView.as_view()
        response = view(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "success"
        assert data["task_id"] == "view-test-task-123"

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
                "QUEUES": ["default"],
                "OPTIONS": {
                    "CLOUD_TASKS_PROJECT": "test-project",
                    "CLOUD_TASKS_LOCATION": "us-central1",
                    "TASK_HANDLER_HOST": "https://test.example.com",
                },
            },
        }
    )
    def test_execute_task_failure(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView
        from tests.tasks import failing_view_task

        factory = RequestFactory()
        payload = {
            "task_id": "view-test-task-456",
            "task_path": f"{failing_view_task.module_path}",
            "args": [],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }

        request = factory.post(
            "/tasks/execute/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        view = ExecuteTaskView.as_view()
        response = view(request)

        # Return 500 for Cloud Tasks retry
        assert response.status_code == 500
        data = json.loads(response.content)
        assert data["status"] == "failed"
        assert len(data["errors"]) == 1
        assert "RuntimeError" in data["errors"][0]["exception"]

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
                "QUEUES": ["default"],
                "OPTIONS": {
                    "CLOUD_TASKS_PROJECT": "test-project",
                    "CLOUD_TASKS_LOCATION": "us-central1",
                    "TASK_HANDLER_HOST": "https://test.example.com",
                },
            },
        }
    )
    def test_failure_traceback_is_logged_not_returned(self, caplog):
        from django_tasks_cloud_tasks.views import ExecuteTaskView
        from tests.tasks import failing_view_task

        payload = {
            "task_id": "view-test-task-789",
            "task_path": failing_view_task.module_path,
            "args": [],
            "kwargs": {},
            "queue_name": "default",
            "backend": "default",
            "priority": 0,
            "takes_context": False,
            "enqueued_at": "2024-01-01T00:00:00+00:00",
        }
        request = RequestFactory().post(
            "/tasks/execute/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        with caplog.at_level(logging.ERROR, logger="django.tasks"):
            response = ExecuteTaskView.as_view()(request)

        assert response.status_code == 500
        assert json.loads(response.content) == {
            "status": "failed",
            "task_id": "view-test-task-789",
            "errors": [{"exception": "builtins.RuntimeError"}],
        }
        [record] = [r for r in caplog.records if r.name == "django.tasks"]
        assert record.levelno == logging.ERROR
        assert "view-test-task-789" in record.getMessage()
        assert isinstance(record.exc_info[1], RuntimeError)

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
                "QUEUES": ["default"],
                "OPTIONS": {
                    "CLOUD_TASKS_PROJECT": "test-project",
                    "CLOUD_TASKS_LOCATION": "us-central1",
                    "TASK_HANDLER_HOST": "https://test.example.com",
                },
            },
        }
    )
    def test_invalid_json_returns_400(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        factory = RequestFactory()
        request = factory.post(
            "/tasks/execute/",
            data="invalid json",
            content_type="application/json",
        )

        view = ExecuteTaskView.as_view()
        response = view(request)

        assert response.status_code == 400
        data = json.loads(response.content)
        assert data["error"] == "Invalid JSON"

    @override_settings(
        TASKS={
            "default": {
                "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
                "QUEUES": ["default"],
                "OPTIONS": {
                    "CLOUD_TASKS_PROJECT": "test-project",
                    "CLOUD_TASKS_LOCATION": "us-central1",
                    "TASK_HANDLER_HOST": "https://test.example.com",
                },
            },
        },
        CLOUD_TASKS_OIDC_AUDIENCE="https://test.example.com",
    )
    def test_unauthorized_without_token(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        factory = RequestFactory()
        request = factory.post(
            "/tasks/execute/",
            data=json.dumps({}),
            content_type="application/json",
        )

        # Mock the auth handler to reject the request
        with patch(
            "django_tasks_cloud_tasks.auth.create_oidc_auth_handler"
        ) as mock_create:
            mock_handler = MagicMock(
                return_value=(False, "Missing or invalid Authorization header")
            )
            mock_create.return_value = mock_handler

            view = ExecuteTaskView.as_view()
            response = view(request)

            assert response.status_code == 401
            data = json.loads(response.content)
            assert data["error"] == "Unauthorized"


def cloud_tasks_options(**options):
    return {
        "default": {
            "BACKEND": "django_tasks_cloud_tasks.CloudTasksBackend",
            "QUEUES": ["default"],
            "OPTIONS": {
                "CLOUD_TASKS_PROJECT": "test-project",
                "CLOUD_TASKS_LOCATION": "us-central1",
                "TASK_HANDLER_HOST": "https://test.example.com",
                **options,
            },
        },
    }


def execute_request(token=None):
    from tests.tasks import simple_task

    payload = {
        "task_id": "view-auth-task",
        "task_path": simple_task.module_path,
        "args": [1],
        "kwargs": {},
        "queue_name": "default",
        "backend": "default",
        "priority": 0,
        "takes_context": False,
        "enqueued_at": "2024-01-01T00:00:00+00:00",
    }
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return RequestFactory().post(
        "/cloudtasks/execute/",
        data=json.dumps(payload),
        content_type="application/json",
        **headers,
    )


GOOGLE_CLAIMS = {"iss": "https://accounts.google.com"}
SERVICE_ACCOUNT = "invoker@test-project.iam.gserviceaccount.com"


@pytest.mark.django_db
class TestExecuteTaskViewAuthentication:
    @override_settings(
        TASKS=cloud_tasks_options(OIDC_SERVICE_ACCOUNT_EMAIL=SERVICE_ACCOUNT)
    )
    def test_backend_with_oidc_rejects_request_without_token(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        response = ExecuteTaskView.as_view()(execute_request())

        assert response.status_code == 401

    @override_settings(
        TASKS=cloud_tasks_options(OIDC_SERVICE_ACCOUNT_EMAIL=SERVICE_ACCOUNT)
    )
    def test_backend_with_oidc_verifies_against_handler_host(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        with patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS
        ) as verify:
            response = ExecuteTaskView.as_view()(execute_request("token"))

        assert response.status_code == 200
        assert verify.call_args.kwargs["audience"] == "https://test.example.com"

    @override_settings(
        TASKS=cloud_tasks_options(
            OIDC_SERVICE_ACCOUNT_EMAIL=SERVICE_ACCOUNT,
            OIDC_AUDIENCE="https://audience.example.com",
        )
    )
    def test_backend_with_oidc_verifies_against_oidc_audience(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        with patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS
        ) as verify:
            response = ExecuteTaskView.as_view()(execute_request("token"))

        assert response.status_code == 200
        assert verify.call_args.kwargs["audience"] == "https://audience.example.com"

    @override_settings(
        TASKS=cloud_tasks_options(OIDC_SERVICE_ACCOUNT_EMAIL=SERVICE_ACCOUNT),
        CLOUD_TASKS_OIDC_AUDIENCE="https://override.example.com",
    )
    def test_audience_setting_overrides_backend(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        with patch(
            "google.oauth2.id_token.verify_oauth2_token", return_value=GOOGLE_CLAIMS
        ) as verify:
            response = ExecuteTaskView.as_view()(execute_request("token"))

        assert response.status_code == 200
        assert verify.call_args.kwargs["audience"] == "https://override.example.com"

    @override_settings(TASKS=cloud_tasks_options())
    def test_backend_without_oidc_does_not_verify(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        with patch(
            "django_tasks_cloud_tasks.detection.detect_default_service_account",
            return_value=None,
        ):
            response = ExecuteTaskView.as_view()(execute_request())

        assert response.status_code == 200

    @override_settings(
        TASKS={
            **cloud_tasks_options(),
            "cloud": cloud_tasks_options(OIDC_SERVICE_ACCOUNT_EMAIL=SERVICE_ACCOUNT)[
                "default"
            ],
        }
    )
    def test_backend_alias_selects_the_backend(self):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        view = ExecuteTaskView.as_view(backend_alias="cloud")
        with patch(
            "django_tasks_cloud_tasks.detection.detect_default_service_account",
            return_value=None,
        ):
            response = view(execute_request())

        assert response.status_code == 401


def valid_payload():
    from tests.tasks import simple_task

    return {
        "task_id": "view-payload-task",
        "task_path": simple_task.module_path,
        "args": [1],
        "kwargs": {},
        "queue_name": "default",
        "backend": "default",
        "priority": 0,
        "takes_context": False,
        "enqueued_at": "2024-01-01T00:00:00+00:00",
    }


def post_payload(payload):
    from django_tasks_cloud_tasks.views import ExecuteTaskView

    request = RequestFactory().post(
        "/cloudtasks/execute/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    return ExecuteTaskView.as_view()(request)


@pytest.mark.django_db
class TestExecuteTaskViewPayloadValidation:
    @pytest.fixture(autouse=True)
    def tasks_settings(self, settings):
        settings.TASKS = cloud_tasks_options()

    @pytest.mark.parametrize(
        "field", ["task_id", "task_path", "args", "kwargs", "queue_name", "backend"]
    )
    def test_missing_field_returns_400(self, field, caplog):
        payload = valid_payload()
        del payload[field]

        with caplog.at_level(logging.ERROR, logger="django_tasks_cloud_tasks"):
            response = post_payload(payload)

        assert response.status_code == 400
        assert json.loads(response.content) == {
            "error": "Invalid payload",
            "detail": f"missing field: {field}",
        }
        [record] = [
            r for r in caplog.records if r.getMessage().startswith("Invalid payload:")
        ]
        assert f"detail=missing field: {field}" in record.getMessage()

    @pytest.mark.parametrize(
        "field, value, detail",
        [
            ("task_path", None, "task_path must be a string"),
            ("args", {"x": 1}, "args must be a list"),
            ("kwargs", [1], "kwargs must be an object"),
            (
                "enqueued_at",
                "yesterday",
                "enqueued_at must be an ISO 8601 date and time",
            ),
        ],
    )
    def test_wrong_type_returns_400(self, field, value, detail):
        payload = valid_payload()
        payload[field] = value

        response = post_payload(payload)

        assert response.status_code == 400
        assert json.loads(response.content)["detail"] == detail

    @pytest.mark.parametrize(
        "payload, json_type",
        [([], "an array"), ("task", "a string"), (1, "a number"), (None, "null")],
    )
    def test_payload_that_is_not_an_object_returns_400(self, payload, json_type):
        response = post_payload(payload)

        assert response.status_code == 400
        assert (
            json.loads(response.content)["detail"]
            == f"the payload must be a JSON object, not {json_type}"
        )

    def test_invalid_payload_runs_nothing(self):
        from django.tasks.signals import task_started

        payload = valid_payload()
        del payload["args"]
        received = []
        task_started.connect(received.append, dispatch_uid="payload-test")
        try:
            response = post_payload(payload)
        finally:
            task_started.disconnect(dispatch_uid="payload-test")

        assert response.status_code == 400
        assert received == []

    def test_valid_payload_runs_the_task(self):
        with patch(
            "django_tasks_cloud_tasks.detection.detect_default_service_account",
            return_value=None,
        ):
            response = post_payload(valid_payload())

        assert response.status_code == 200

    def test_invalid_payload_log_names_the_task_and_the_cloud_task(self, caplog):
        from django_tasks_cloud_tasks.views import ExecuteTaskView

        payload = valid_payload()
        payload["args"] = {"secret": "value"}
        request = RequestFactory().post(
            "/cloudtasks/execute/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CLOUDTASKS_QUEUENAME="default",
            HTTP_X_CLOUDTASKS_TASKNAME="view-payload-task",
            HTTP_X_CLOUDTASKS_TASKRETRYCOUNT="3",
        )

        with caplog.at_level(logging.ERROR, logger="django_tasks_cloud_tasks"):
            ExecuteTaskView.as_view()(request)

        [record] = [
            r for r in caplog.records if r.getMessage().startswith("Invalid payload:")
        ]
        message = record.getMessage()
        assert record.levelno == logging.ERROR
        assert "detail=args must be a list" in message
        assert "id=view-payload-task" in message
        assert "path=tests.tasks.simple_task" in message
        assert "keys=['args', 'backend'," in message
        assert "queue=default" in message
        assert "cloud_task=view-payload-task" in message
        assert "retry_count=3" in message
        assert "secret" not in message

    def test_task_that_cannot_be_imported_returns_500_failed(self):
        payload = valid_payload()
        payload["task_path"] = "tests.tasks.no_such_task"

        response = post_payload(payload)

        assert response.status_code == 500
        assert json.loads(response.content) == {
            "status": "failed",
            "task_id": "view-payload-task",
            "errors": [{"exception": "builtins.ImportError"}],
        }
