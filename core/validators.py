import os
from django.core.exceptions import ValidationError

def validate_file_size(value):
    """
    Valida que el archivo no supere los 5MB.
    """
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('El archivo no puede pesar más de 5MB.')

def validate_image_extension(value):
    """
    Valida que la extensión del archivo sea una de las permitidas para imágenes.
    """
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if not ext.lower() in valid_extensions:
        raise ValidationError(
            f'Formato de archivo "{ext}" no soportado. Use: .jpg, .jpeg, .png o .webp'
        )
