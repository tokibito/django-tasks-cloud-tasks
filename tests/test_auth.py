"""Tests for auth.py"""

import logging
from unittest.mock import patch

from django.test import RequestFactory


class TestOIDCAuthHandler:
    def test_verification_failure_is_logged_once(self, caplog, capsys):
        from django_tasks_cloud_tasks.auth import create_oidc_auth_handler

        request = RequestFactory().post(
            "/cloudtasks/execute/",
            HTTP_AUTHORIZATION="Bearer bad-token",
        )

        with patch(
            "google.oauth2.id_token.verify_oauth2_token",
            side_effect=ValueError("Token expired"),
        ):
            handler = create_oidc_auth_handler("https://test.example.com")
            with caplog.at_level(logging.ERROR, logger="django_tasks_cloud_tasks"):
                is_valid, error_message = handler(request)

        assert is_valid is False
        assert error_message == "Token expired"
        assert [r.getMessage() for r in caplog.records] == [
            "OIDC token verification failed: Token expired"
        ]
        assert capsys.readouterr().err == ""
