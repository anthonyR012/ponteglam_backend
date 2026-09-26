from rest_framework.throttling import AnonRateThrottle

class LoginRateThrottle(AnonRateThrottle):
    """
    Control de flujo específico para endpoints de autenticación.
    Aplica para usuarios no autenticados basándose en su IP.
    """
    scope = 'login'
