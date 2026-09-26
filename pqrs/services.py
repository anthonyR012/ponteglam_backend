from .models import PQRS


def crear_pqrs(datos_validados: dict) -> PQRS:
    """
    Encapsula la creación de una PQRS para que las vistas no manipulen
    el modelo directamente y sea fácil añadir efectos secundarios
    (emails, notificaciones, logs) sin tocar la vista.
    """
    return PQRS.objects.create(**datos_validados)


def consultar_por_radicado(radicado: str) -> PQRS | None:
    """
    Búsqueda insensible a mayúsculas para tolerar errores de tipeo del ciudadano.
    """
    return PQRS.objects.filter(radicado__iexact=radicado.strip()).first()