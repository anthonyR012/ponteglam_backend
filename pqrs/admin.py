from django.contrib import admin
from .models import PQRS


@admin.register(PQRS)
class PQRSAdmin(admin.ModelAdmin):
    list_display = ('radicado', 'tipo', 'nombre_completo', 'email', 'estado', 'created_at')
    list_filter = ('tipo', 'estado', 'created_at')
    search_fields = ('radicado', 'nombre_completo', 'email', 'documento_identidad')
    readonly_fields = ('radicado', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Radicado', {
            'fields': ('radicado', 'tipo', 'estado')
        }),
        ('Ciudadano', {
            'fields': ('nombre_completo', 'email', 'telefono', 'documento_identidad')
        }),
        ('Solicitud', {
            'fields': ('asunto', 'descripcion')
        }),
        ('Gestión interna', {
            'fields': ('respuesta',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )