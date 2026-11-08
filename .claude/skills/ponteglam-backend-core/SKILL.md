---
name: ponteglam-backend-core
description: Componentes globales del backend PonteGlam en la app core — MixinAudit, FileMixin, catálogo Category/Type (estados y tipos), borrado lógico con auditoría, managers, utilidades de fecha/moneda/distancia, helpers de ownership, throttles, validadores de imagen y middleware de sanitización. Úsala al crear o modificar modelos, al necesitar un estado/tipo, al subir archivos, al verificar que un recurso pertenece al usuario o al trabajar con fechas.
---

# Componentes globales (`core`)

## 1. `MixinAudit` — base de casi todos los modelos

```python
from core.models import MixinAudit

class MiModelo(MixinAudit):
    ...
```

Aporta `created_at`, `updated_at`, `created_by_user_id` (**obligatorio**, `PositiveIntegerField`, no FK)
y `modified_by_user_id`. Al crear siempre pasar `created_by_user_id=request.user.pk`.
Para acciones del sistema (tareas Celery) el código usa `created_by_user_id=1`.

`created_by_user_id` es también el **dueño** del recurso: `Company`, `Service`, `Headquarter`
pertenecen a quien los creó. Ver helpers de ownership abajo.

## 2. `FileMixin` — modelos con imagen

```python
from core.models import FileMixin

class CompanyFile(FileMixin):
    @staticmethod
    def generate_file_name(instance, filename):
        return f'companies/{instance.company.name}/{filename}'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_file')
```

Da `file` (ImageField con `validate_file_size` ≤5 MB y `validate_image_extension`: jpg, jpeg, png, webp)
y `type` (FK a `core.Type` de la categoría `type_file`). Hay que implementar `generate_file_name`.
`ServiceFile` es anterior y no usa el mixin, pero sigue la misma idea.

Tipos de archivo (`type_file`): `main_image`, `additional_image`, `profile_image`, `cover_image`,
`service_image`, `icon`. Constante: `core.constants.PROFILE_IMAGE`.
Convención: empresa → `profile_image` (logo) + `cover_image`; sede → primera `profile_image`, resto
`additional_image`; servicio → `service_image`.

URLs absolutas: siempre con el host de la request (`request.build_absolute_uri('/')`), como hacen
`Service.get_url_images(host)` y `Headquarter.get_company_picture_url(host)`.

## 3. Catálogo `Category` / `Type`

Estados y tipos configurables viven en BD, no en enums de Python:
`Category(code)` agrupa `Type(code, description)`.

```python
from core.models import Type

estado = Type.objects.get_type(code='available', category_type_code='status_service')
Service.objects.filter(state__code='available')
```

Categorías existentes (código → tipos):

| Category | Types |
|---|---|
| `status_service` | creating, available, unavailable, busy |
| `status_company` / `status_headquarter` | creating, available, unavailable, on_vacation |
| `status_service_category` | active, inactive |
| `status_user` | creating, active, inactive |
| `status_appointment` | pending_payment, active, in_progress, completed, cancelled |
| `status_legal_content` | active, inactive |
| `type_file` | main_image, additional_image, profile_image, cover_image, service_image, icon |
| `type_company` | independent, employer |
| `type_headquarter` | main, others |
| `type_user` | admin, user |
| `gender_service` | male, female, kid, pet, women_men, any_person, no_specified |
| `gender_user` | male, female, no_specified |
| `address_user` | other, house, job |
| `login_of` | by_gmail, by_credentials |
| `legal_content_category` | terms_and_conditions, privacy_policy, service_fee_policy, supplier_usage_notice |
| `global_config` | enable_cancellation_fees (`description` = "true"/"false") |

Reglas:
- Filtrar por `state__code`, nunca por id (los ids cambian entre entornos).
- Un estado nuevo se agrega en `core/scripts/default_settings.json` (para que la semilla lo cree) **y** en la BD.
- Excepción: `Appointment.status` es un `CharField` con constantes (`STATUS_PENDING`…); el FK `state` es legado. Para citas usar **`status`**.
- El app recibe estos códigos como datos (`/core/api/list-types`), así que renombrar un código rompe el app.

## 4. Borrado lógico + auditoría + purga diferida

Patrón de `Company`, `Headquarter` y `Service`:

```python
is_deleted = models.BooleanField(default=False)
deleted_at = models.DateTimeField(null=True, blank=True)

objects = <X>ActiveManager()     # excluye is_deleted=True
all_objects = models.Manager()   # incluye borrados
```

Flujo al eliminar (ver `DeleteService`):
1. Validar que no haya citas `pending`/`active`.
2. Marcar `is_deleted=True`, `deleted_at=timezone.now()`.
3. Crear `<X>DeletionAudit` con `scheduled_deletion_date = now + 5 días`.
4. Programar `permanently_delete_<x>_task.apply_async(args=[id], eta=scheduled_date)`.
5. `cleanup_expired_<x>_task` es el respaldo si el worker perdió el ETA.

Ojo: el manager por defecto **no aplica a joins**. En filtros a través de relaciones
(`service_category__is_deleted`) hay que filtrar `is_deleted=False` explícitamente.

## 5. Managers

- `core.managers.TypeManager.get_type(code, category_type_code)`.
- `services.managers.ServiceManager` (excluye borrados) y `ServiceCategoryManager.with_available_services()`.
- `CompanyActiveManager`, `HeadquarterActiveManager`, `UserNotificationManager`, `UserTermsAndConditionsManager`.

Una query que se repite o tiene más de 2 condiciones va a un manager con docstring de propósito.

## 6. Utilidades (`core/utils.py`)

| Función | Uso |
|---|---|
| `CustomPagination` | `PageNumberPagination` con `page_size = 15` |
| `calculate_km_between_two_points(a, b)` | Distancia haversine en km, 1 decimal |
| `parse_aware_datetime(str)` | ISO 8601 **con offset** → datetime UTC aware (rechaza naive) |
| `get_local_time(dt, tz_name)` | UTC → zona IANA (para lógica por hora local y mensajes) |
| `now_in_tz(tz_name)` | Hora actual en la zona |
| `format_currency(amount)` | `$25.000` (pesos colombianos) |
| `calculate_cancellation_fee(start, total)` | Multa según `CancellationRule` y `global_config` |

Fechas: `timezone.now()` siempre; `tz_name = settings.TIME_ZONE`. Nunca comparar `.date()` de UTC con hora local.

## 7. Ownership (`core/permissions.py`)

```python
from core.permissions import get_owned_object, not_found_response, verify_headquarter_ownership

service = get_owned_object(models.Service, pk, request.user)   # filtra created_by_user_id
if not service:
    return not_found_response('Servicio no encontrado o no tienes permiso.')
```

- `get_owned_object(model, pk, user)` → por `created_by_user_id`.
- `get_user_object(model, pk, user)` → por FK `user`.
- `verify_headquarter_ownership(hq_id, user)` → la sede es de una empresa del usuario.
- `ownership_denied_response()` (403) y `not_found_response()` (404) con `{'error': ...}`.

Preferir 404 sobre 403 cuando el recurso no es del usuario (no revelar que existe).

## 8. Seguridad transversal

- `core.middleware.DataSanitizationMiddleware`: aplica `strip_tags` y elimina palabras SQL
  (SELECT, DROP, UNION…) de **todo** string en POST/PUT/PATCH, salvo `password`, `email`, `token`,
  `google_access_token`, `uuid_google`… Consecuencia: un campo de texto libre nunca conservará
  esas palabras. Si un campo nuevo debe conservarlas, agregarlo a `SENSITIVE_FIELDS`.
- `core.throttles.LoginRateThrottle` (scope `login`, 5/min). Tasas globales: anon 15/min, user 20/min.
- Validadores: `core.validators.validate_file_size`, `validate_image_extension`.

## 9. Logs del app móvil

`core.MobileAppLog` recibe errores del app (`/core/api/create-mobile-app-log/`) y
`core.tasks.cleanup_mobile_logs` los purga cada 30 días. Útil para depurar fallos reportados.
