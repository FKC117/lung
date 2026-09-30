"""Small, intentionally non-persistent endpoint for client error telemetry."""

import json
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


logger = logging.getLogger("frontend")


def _text(value: object, limit: int) -> str:
    """Return bounded text so browser reports cannot turn logs into data dumps."""
    return str(value or "").replace("\x00", " ").strip()[:limit]


@api_view(["POST"])
@permission_classes([AllowAny])
def client_error(request):
    """Record a sanitized browser failure in the Django log and acknowledge it.

    This endpoint deliberately has no database write: browser errors can be
    frequent, contain clinical form text, and must not become patient records.
    """
    payload = request.data if isinstance(request.data, dict) else {}
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    safe_context = {
        key: _text(value, 240)
        for key, value in context.items()
        if key in {"kind", "method", "path", "status"}
    }
    logger.error(
        "client_error message=%r context=%s stack=%r",
        _text(payload.get("message"), 2_000),
        json.dumps(safe_context, ensure_ascii=True, sort_keys=True),
        _text(payload.get("stack"), 8_000),
    )
    return Response(status=204)
