import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class PQRS(models.Model):

    class TipoChoices(models.TextChoices):
        PETICION = 'PETICION', _('Petición')
        QUEJA = 'QUEJA', _('Queja')
        RECLAMO = 'RECLAMO', _('Reclamo')
        SUGERENCIA = 'SUGERENCIA', _('Sugerencia')
        DENUNCIA = 'DENUNCIA', _('Denuncia')

    class EstadoChoices(models.TextChoices):
        RECIBIDO = 'RECIBIDO', _('Recibido')
        EN_PROCESO = 'EN_PROCESO', _('En proceso')
        RESUELTO = 'RESUELTO', _('Resuelto')
        CERRADO = 'CERRADO', _('Cerrado')
        RECHAZADO = 'RECHAZADO', _('Rechazado')

    # El radicado se genera una sola vez al crear el registro.
    # Usamos UUID4 truncado para que sea legible pero único.
    radicado = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoChoices.choices,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.RECIBIDO,
    )

    # Datos del ciudadano
    nombre_completo = models.CharField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    documento_identidad = models.CharField(max_length=30, blank=True)

    asunto = models.CharField(max_length=300)
    descripcion = models.TextField()

    # Respuesta interna — no se expone al ciudadano hasta que el estado lo justifique
    respuesta = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('PQRS')
        verbose_name_plural = _('PQRS')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.radicado} — {self.get_tipo_display()}'

    def save(self, *args, **kwargs):
        # El radicado se asigna una única vez; nunca se sobreescribe en actualizaciones.
        if not self.radicado:
            self.radicado = self._generar_radicado()
        super().save(*args, **kwargs)

    @staticmethod
    def _generar_radicado() -> str:
        from django.utils import timezone
        prefijo = timezone.now().strftime('%Y%m')
        sufijo = uuid.uuid4().hex[:6].upper()
        return f'PQR-{prefijo}-{sufijo}'

    @property
    def estado_color(self) -> str:
        colores = {
            'RECIBIDO': 'info',
            'EN_PROCESO': 'warning',
            'RESUELTO': 'success',
            'CERRADO': 'secondary',
            'RECHAZADO': 'danger',
        }
        return colores.get(self.estado, 'secondary')

    @property
    def tiene_respuesta(self) -> bool:
        return bool(self.respuesta)