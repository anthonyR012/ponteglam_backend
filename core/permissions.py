from rest_framework import status
from rest_framework.response import Response


def get_owned_object(model_class, pk, user, error_msg=None):
    """Retorna un objeto si fue creado por el usuario, o None si no existe o no es suyo."""
    return model_class.objects.filter(
        pk=pk, created_by_user_id=user.pk
    ).first()


def get_user_object(model_class, pk, user, error_msg=None):
    """Retorna un objeto que pertenece directamente al usuario (campo user), o None."""
    return model_class.objects.filter(pk=pk, user=user).first()


def verify_headquarter_ownership(headquarter_id, user):
    """Verifica que una sede pertenezca a una empresa creada por el usuario."""
    from headquarters.models import Headquarter
    return Headquarter.objects.filter(
        pk=headquarter_id,
        company__created_by_user_id=user.pk
    ).exists()


def ownership_denied_response(msg=None):
    """Respuesta estándar de ownership denegado."""
    return Response(
        {'error': msg or 'No tienes permiso para realizar esta acción.'},
        status=status.HTTP_403_FORBIDDEN
    )


def not_found_response(msg=None):
    """Respuesta estándar de recurso no encontrado."""
    return Response(
        {'error': msg or 'Recurso no encontrado.'},
        status=status.HTTP_404_NOT_FOUND
    )
