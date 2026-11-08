---
name: ponteglam-backend-api-endpoints
description: Cómo crear o modificar endpoints DRF en el backend PonteGlam siguiendo el patrón real del proyecto — un ViewSet por acción, router kebab-case por app, sobre de respuesta {"success"|"error"|"detail"}, TokenAuthentication, ownership por created_by_user_id, serializers con request en el contexto, paginación, caché Redis y throttling. Úsala siempre que agregues, cambies o revises una vista, serializer o ruta de API.
---

# Endpoints DRF en PonteGlam

## Patrón del proyecto: un ViewSet por acción

Cada operación es su propia clase con **un solo** método (`list`, `create`, `retrieve`,
`partial_update`, `update` o `destroy`) y su propia ruta kebab-case con verbo:
`create-service-addon`, `update-service-addon`, `delete-service-addon`, `list-service-addons`.
No se usan `ModelViewSet` CRUD completos ni `@action` (salvo casos aislados).

### 1. Vista (`<app>/api/views.py`)

```python
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.permissions import get_owned_object, not_found_response
from services import models
from services.api import serializers


class UpdateService(viewsets.ViewSet):
    """Permite al proveedor editar uno de sus servicios."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def partial_update(self, request: Request, pk=None):
        service = get_owned_object(models.Service, pk, request.user)
        if not service:
            return not_found_response('Servicio no encontrado o sin permisos.')

        serializer = serializers.CreateServiceSerializer(
            service, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save(modified_by_user_id=request.user.pk)
        return Response({'success': serializer.data}, status=status.HTTP_200_OK)
```

### 2. Router (`<app>/api/routers.py`)

```python
router.register(r'update-service', views.UpdateService, basename='update-service')
```

URL resultante: `/<app>/api/update-service/<pk>/`. Los routers se incluyen en
`ponteglam/urls.py` (`path('<app>/api/', include(<app>_router.urls))`). Una app nueva
necesita su router registrado ahí.

Mapeo método → URL que genera DefaultRouter:

| Método del ViewSet | HTTP | URL |
|---|---|---|
| `list` | GET | `/<prefix>/` |
| `create` | POST | `/<prefix>/` |
| `retrieve` | GET | `/<prefix>/<pk>/` |
| `partial_update` | PATCH | `/<prefix>/<pk>/` |
| `update` | PUT | `/<prefix>/<pk>/` |
| `destroy` | DELETE | `/<prefix>/<pk>/` |

## Sobre de respuesta (contrato con el app)

| Caso | Forma | Status |
|---|---|---|
| Éxito | `{"success": <data o mensaje>}` | 200 / 201 |
| Error de validación o negocio | `{"error": <mensaje o serializer.errors>}` | 400 / 403 / 404 |
| Regla de negocio que el app muestra tal cual | `{"detail": "<mensaje en español>"}` | 400 |
| Listado paginado | `{"count", "next", "previous", "results"}` | 200 |

El app Flutter decide qué mostrar según estas llaves (`keySuccess`, `keyErr`, `keyDetail`).
**No inventes llaves nuevas** en la raíz. Ver skill `ponteglam-api-contract`.
Mensajes al usuario: en español, sin trazas ni nombres de modelos.

## Autenticación y permisos

- Por defecto: `TokenAuthentication` + `IsAuthenticated`. Declarar siempre ambos explícitamente.
- Endpoints públicos (catálogos, categorías): `permission_classes = [AllowAny]`.
- Auth/login: agregar `throttle_classes = [LoginRateThrottle]`.
- Ownership: `get_owned_object` / `verify_headquarter_ownership` (skill `ponteglam-backend-core`).
  Nunca confiar en un `user_id` que venga en el body.
- Roles: no hay campo de rol. **Proveedor** = usuario que creó una `Company`
  (`company.created_by_user_id`); **trabajador** = `Worker.user`; el resto son clientes.
  Un mismo usuario puede ser cliente y proveedor.

## Serializers

- `ModelSerializer` por caso de uso (`CreateServiceSerializer` ≠ `ServiceSerializer` ≠ `ServiceDetailSerializer`).
- Validación en `validate_<campo>` y `validate`; nunca validar a mano en la vista lo que puede hacer el serializer.
- Pasar `context={'request': request}` cuando el serializer arma URLs o depende del usuario:
  `self.context.get('request').build_absolute_uri('/')` construye el host para imágenes.
- Campos calculados con `SerializerMethodField` + `get_<campo>`; si hace queries, preferir
  `select_related`/`prefetch_related` en la vista o anotar en el manager para evitar N+1.

## Listados

- Paginación: `core.utils.CustomPagination` (15 por página) con `self.paginate_queryset(...)` y
  `self.get_paginated_response(...)`.
- Filtros por `request.query_params`. Si el filtro cambia la forma de la respuesta para un
  consumidor concreto, usar un parámetro opcional con default compatible
  (ejemplo real: `list-categories-services?include_empty=true`).
- Caché (`ListServices`): `cache.get/set(cache_key, data, timeout=50)`.
  **La cache key debe incluir TODOS los parámetros que alteran el resultado** (usuario, página,
  filtros). Ya hubo un bug por omitir filtros. Al cambiar datos que afectan un listado cacheado,
  recordar que puede seguir sirviéndose hasta 50 s.

## Fechas en la API

- Entrada: ISO 8601 **con offset**, parseado con `core.utils.parse_aware_datetime`.
- Salida: `REST_FRAMEWORK['DATETIME_FORMAT'] = '%Y-%m-%dT%H:%M:%S%z'`.

## Efectos secundarios

- Correo, push, recordatorios: **siempre** vía Celery (`.delay` / `.apply_async`), nunca síncronos en la vista.
- Registros en BD que el usuario debe ver de inmediato (notificación in-app) se crean síncronos
  y solo el push va a la cola (ver `ponteglam-backend-notifications`).

## Checklist antes de terminar

- [ ] `authentication_classes` y `permission_classes` explícitos.
- [ ] Ownership verificado para todo recurso con `pk`.
- [ ] Respuesta con `success` / `error` / `detail`, status HTTP correcto.
- [ ] `created_by_user_id` / `modified_by_user_id` seteados.
- [ ] Ruta registrada en `api/routers.py` y (si es app nueva) en `ponteglam/urls.py`.
- [ ] Constante del endpoint agregada en el app: `lib/config/constant/end_point_constant.dart`.
- [ ] Si cambia un listado cacheado: cache key revisada.
- [ ] Probado con curl contra el servidor local (`Authorization: Token <token>`).

```bash
TOKEN=$(curl -s -X POST localhost:8000/api-token-auth/ -d username=cliente_prueba -d password='Cliente123!' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['user']['token'])")
curl -s -H "Authorization: Token $TOKEN" localhost:8000/services/api/list-services/
```
