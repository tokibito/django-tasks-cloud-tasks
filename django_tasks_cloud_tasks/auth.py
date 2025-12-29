"""Cloud Tasks OIDC authentication."""

import functools
import logging
import sys

from django.http import JsonResponse

logger = logging.getLogger("django_tasks_cloud_tasks")

# Google OIDC token issuers
GOOGLE_ISSUERS = [
    "https://accounts.google.com",
    "accounts.google.com",
]


def create_oidc_auth_handler(audience):
    """
    Create OIDC authentication handler.

    Args:
        audience: Audience value for token verification

    Returns:
        Authentication handler function
    """
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    def auth_handler(request):
        """
        Verify OIDC token in request.

        Returns:
            (bool, Optional[str]): (verification success flag, error message)
        """
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return False, "Missing or invalid Authorization header"

        token = auth_header[7:]

        try:
            claims = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                audience=audience,
            )

            # Verify issuer
            if claims.get("iss") not in GOOGLE_ISSUERS:
                return False, f"Invalid issuer: {claims.get('iss')}"

            return True, None

        except Exception as e:
            logger.error(f"OIDC token verification failed: {e}")
            print(f"OIDC token verification failed: {e}", file=sys.stderr)
            return False, str(e)

    return auth_handler


def verify_cloud_tasks_oidc(audience=None):
    """
    Decorator to verify Cloud Tasks OIDC token.

    Args:
        audience: Audience value for token verification.
                  If None, retrieved from Django settings.

    Usage:
        @verify_cloud_tasks_oidc(audience="https://your-app.run.app")
        def execute_task(request):
            ...
    """

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Determine audience
            aud = audience
            if aud is None:
                from django.conf import settings

                aud = getattr(settings, "CLOUD_TASKS_OIDC_AUDIENCE", None)

            if aud is None:
                # Skip verification if audience is not configured
                return view_func(request, *args, **kwargs)

            auth_handler = create_oidc_auth_handler(aud)
            is_valid, error_message = auth_handler(request)

            if not is_valid:
                return JsonResponse(
                    {"error": "Unauthorized", "detail": error_message},
                    status=401,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
