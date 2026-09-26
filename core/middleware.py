import json
import re

from django.utils.html import strip_tags


SENSITIVE_FIELDS = frozenset({
    'password',
    'old_password',
    'new_password',
    'email',
    'token',
    'google_access_token',
    'uuid_google',
})

SQL_INJECTION_PATTERN = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|UNION|"
    r"TRUNCATE|DECLARE)\b)",
    re.IGNORECASE,
)


class DataSanitizationMiddleware:
    """Middleware global que sanitiza strings de entrada contra XSS y SQL injection.

    Aplica strip_tags y limpieza de patrones peligrosos a todos los campos
    de texto entrantes, exceptuando campos sensibles como contraseñas,
    emails y tokens que necesitan conservar sus caracteres especiales.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ('POST', 'PUT', 'PATCH'):
            self._sanitize_post(request)
            self._sanitize_json(request)

        return self.get_response(request)

    def _sanitize_post(self, request):
        if not request.POST:
            return
        mutable = request.POST.copy()
        for key in mutable:
            if key not in SENSITIVE_FIELDS:
                mutable[key] = self._clean(mutable[key])
        request.POST = mutable

    def _sanitize_json(self, request):
        content_type = getattr(request, 'content_type', '') or ''
        if 'application/json' not in content_type or not request.body:
            return
        try:
            data = json.loads(request.body)
            sanitized = self._sanitize_value(data)
            request._body = json.dumps(sanitized).encode('utf-8')
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    def _sanitize_value(self, value, field_name=None):
        if isinstance(value, dict):
            return {
                k: self._sanitize_value(v, field_name=k)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str) and field_name not in SENSITIVE_FIELDS:
            return self._clean(value)
        return value

    @staticmethod
    def _clean(value):
        """Elimina etiquetas HTML y patrones de inyección SQL de un string."""
        value = strip_tags(value)
        value = SQL_INJECTION_PATTERN.sub('', value)
        return value.strip()
