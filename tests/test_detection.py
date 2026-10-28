"""Tests for detection.py"""

from unittest.mock import patch

import pytest

CLOUD_RUN_METADATA = {
    "project/numeric-project-id": "123456789012",
    "instance/region": "projects/123456789012/regions/asia-northeast1",
}


def cloud_run_metadata(path):
    return CLOUD_RUN_METADATA.get(path)


class TestIsCloudRun:
    def test_returns_true_when_k_service_is_set(self):
        from django_tasks_cloud_tasks import is_cloud_run

        with patch.dict("os.environ", {"K_SERVICE": "my-service"}):
            assert is_cloud_run() is True

    def test_returns_false_when_k_service_is_not_set(self):
        from django_tasks_cloud_tasks import is_cloud_run

        with patch.dict("os.environ", {}, clear=True):
            assert is_cloud_run() is False


class TestIsAppEngine:
    def test_returns_true_when_gae_application_is_set(self):
        from django_tasks_cloud_tasks import is_app_engine

        with patch.dict("os.environ", {"GAE_APPLICATION": "e~my-project"}):
            assert is_app_engine() is True

    def test_returns_false_when_gae_application_is_not_set(self):
        from django_tasks_cloud_tasks import is_app_engine

        with patch.dict("os.environ", {}, clear=True):
            assert is_app_engine() is False


class TestDetectGcpProject:
    def test_detects_from_google_cloud_project_env(self):
        from django_tasks_cloud_tasks import detect_gcp_project

        with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "my-project"}):
            assert detect_gcp_project() == "my-project"

    def test_detects_from_gae_application_env(self):
        from django_tasks_cloud_tasks import detect_gcp_project

        with patch.dict(
            "os.environ",
            {"GAE_APPLICATION": "asia-northeast1~my-gae-project"},
            clear=True,
        ):
            assert detect_gcp_project() == "my-gae-project"

    def test_returns_none_when_not_detected(self):
        from django_tasks_cloud_tasks import detect_gcp_project

        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata", return_value=None
            ):
                assert detect_gcp_project() is None


class TestDetectGcpLocation:
    def test_detects_from_cloud_tasks_location_env(self):
        from django_tasks_cloud_tasks import detect_gcp_location

        with patch.dict("os.environ", {"CLOUD_TASKS_LOCATION": "asia-northeast1"}):
            assert detect_gcp_location() == "asia-northeast1"

    def test_detects_from_cloud_run_region_env_with_deprecation_warning(self):
        from django_tasks_cloud_tasks import detect_gcp_location

        with patch.dict(
            "os.environ",
            {"K_SERVICE": "my-service", "CLOUD_RUN_REGION": "us-central1"},
            clear=True,
        ):
            with pytest.warns(DeprecationWarning, match="CLOUD_RUN_REGION"):
                assert detect_gcp_location() == "us-central1"

    def test_detects_cloud_run_region_from_metadata(self):
        from django_tasks_cloud_tasks import detect_gcp_location

        with patch.dict("os.environ", {"K_SERVICE": "my-service"}, clear=True):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata",
                side_effect=cloud_run_metadata,
            ):
                assert detect_gcp_location() == "asia-northeast1"

    def test_returns_none_when_not_detected(self):
        from django_tasks_cloud_tasks import detect_gcp_location

        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata", return_value=None
            ):
                assert detect_gcp_location() is None


class TestDetectTaskHandlerHost:
    def test_detects_cloud_run_url_from_metadata(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {
                "K_SERVICE": "my-service",
                "K_REVISION": "my-service-00001-abc",
                "GOOGLE_CLOUD_PROJECT": "my-project",
            },
            clear=True,
        ):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata",
                side_effect=cloud_run_metadata,
            ):
                result = detect_task_handler_host()

        # The project number, not the ID, and no revision prefix.
        assert result == "https://my-service-123456789012.asia-northeast1.run.app"

    def test_detects_cloud_run_url_with_cloud_run_region_env(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {"K_SERVICE": "my-service", "CLOUD_RUN_REGION": "us-central1"},
            clear=True,
        ):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata",
                side_effect=cloud_run_metadata,
            ):
                with pytest.warns(DeprecationWarning, match="CLOUD_RUN_REGION"):
                    result = detect_task_handler_host()

        assert result == "https://my-service-123456789012.us-central1.run.app"

    def test_cloud_run_url_needs_the_project_number(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {"K_SERVICE": "my-service", "GOOGLE_CLOUD_PROJECT": "my-project"},
            clear=True,
        ):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata", return_value=None
            ):
                assert detect_task_handler_host() is None

    def test_no_cloud_run_url_for_a_service_name_too_long_for_it(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        # 50 + 1 + 12 characters: one more than a DNS label allows.
        with patch.dict("os.environ", {"K_SERVICE": "s" * 51}, clear=True):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata",
                side_effect=cloud_run_metadata,
            ):
                assert detect_task_handler_host() is None

    def test_service_url_takes_precedence_on_cloud_run(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {"K_SERVICE": "my-service", "SERVICE_URL": "https://tasks.example.com"},
            clear=True,
        ):
            with patch(
                "django_tasks_cloud_tasks.detection._get_metadata",
                side_effect=cloud_run_metadata,
            ):
                assert detect_task_handler_host() == "https://tasks.example.com"

    def test_detects_app_engine_url(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {
                "GAE_APPLICATION": "asia-northeast1~my-gae-project",
                "GAE_VERSION": "20240101t123456",
            },
            clear=True,
        ):
            result = detect_task_handler_host()
            assert result == "https://20240101t123456-dot-my-gae-project.appspot.com"

    def test_detects_app_engine_url_for_default_service(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {
                "GAE_APPLICATION": "asia-northeast1~my-gae-project",
                "GAE_SERVICE": "default",
                "GAE_VERSION": "20240101t123456",
            },
            clear=True,
        ):
            result = detect_task_handler_host()
            assert result == "https://20240101t123456-dot-my-gae-project.appspot.com"

    def test_detects_app_engine_url_for_other_service(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict(
            "os.environ",
            {
                "GAE_APPLICATION": "asia-northeast1~my-gae-project",
                "GAE_SERVICE": "api",
                "GAE_VERSION": "20240101t123456",
            },
            clear=True,
        ):
            result = detect_task_handler_host()
            assert (
                result
                == "https://20240101t123456-dot-api-dot-my-gae-project.appspot.com"
            )

    def test_returns_none_when_not_in_gcp_environment(self):
        from django_tasks_cloud_tasks import detect_task_handler_host

        with patch.dict("os.environ", {}, clear=True):
            assert detect_task_handler_host() is None
