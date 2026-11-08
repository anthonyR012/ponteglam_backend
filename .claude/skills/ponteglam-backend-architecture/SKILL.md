---
name: ponteglam-backend-architecture
description: Mapa de la arquitectura del backend Django de PonteGlam (apps, capas, dónde va cada pieza, settings, infraestructura local y reglas obligatorias). Úsala SIEMPRE antes de crear o mover código en ponteglam_backend, al decidir en qué app o archivo va una funcionalidad, o cuando necesites entender cómo se conectan Django, DRF, Celery, Redis, Channels y Firebase en este proyecto.
---

# Arquitectura del backend PonteGlam

Django 5.0.2 + DRF + Celery + Redis + Channels + Firebase (FCM). PostgreSQL.
Proyecto Django: `ponteglam/` (settings, urls, celery, asgi). Sin carpeta `apps/`:
cada app vive en la raíz del repo.

## Mapa de apps

| App | Responsabilidad | Prefijo URL |
|---|---|---|
| `core` | Componentes globales: modelos base (`MixinAudit`, `FileMixin`), catálogo `Category`/`Type`, utilidades, permisos, throttles, validadores, middleware de sanitización, logs de la app móvil, contenido legal | `core/api/` y `''` |
| `users` | `User` (AUTH_USER_MODEL), registro, login (`CustomAuthToken`), verificación por correo, direcciones, términos | `users/`, `users/api/`, `api-token-auth/` |
| `companies` | `Company` (empresa del proveedor), archivos, Nequi, borrado diferido | `companies/api/` |
| `headquarters` | `Headquarter` (sede), horarios por día, likes, servicios por sede, trabajadores por sede | `headquarters/api/` |
| `services` | `Service`, `ServiceCategory`, **citas** (`Appointment`), disponibilidad, cancelación, reprogramación, WebSocket de agenda | `services/api/` |
| `workers` | `Worker`, invitaciones, bloqueos, gestión de staff | `workers/api/` |
| `addons` | Adicionales de servicio y su vínculo con citas | `addons/api/` |
| `ratings` | Calificaciones sede-servicio y respuestas | `ratings/api/` |
| `notifications` | Notificaciones in-app, push FCM, tokens de dispositivo, tareas de recordatorio | `notifications/api/` |
| `transactions` | `Wallet`, `WalletTransaction`, `Fee`, `Transaction` (deuda/saldo) | `transactions/api/` |
| `pqrs` | PQRS con formulario y plantillas Django (no DRF) | `pqrs/` |
| `chats` | Chat por WebSocket | `chats/api/`, ws `chat/` |
| `blogs`, `reports` | Módulos menores | `blogs/api/`, `reports/api/` |

## Estructura interna de una app (la real)

```
<app>/
├── models.py          # modelos + managers propios (o managers.py si crecen)
├── managers.py        # queries reutilizables (services, core)
├── tasks.py           # tareas Celery (@shared_task)
├── signals.py         # señales (ej. transactions crea Wallet al crear User)
├── api/
│   ├── routers.py     # DefaultRouter, una ruta kebab-case por ViewSet
│   ├── views.py       # un ViewSet por acción
│   └── serializers.py
├── ws/                # consumers.py + routing.py (solo services y chats)
├── scripts/           # create_default_settings.py + default_settings.json (semillas)
└── tests.py
```

`views.py` en la raíz de la app normalmente está vacío; la lógica HTTP está en `api/views.py`.

## Dónde va cada cosa

| Necesito… | Va en |
|---|---|
| Endpoint nuevo | `<app>/api/views.py` + registrar en `<app>/api/routers.py` → skill `ponteglam-backend-api-endpoints` |
| Query reutilizable o compleja | Manager en `<app>/managers.py` o en `models.py` (nunca inline en la vista si se repite) |
| Validación de entrada | Serializer (`validate_<campo>`, `validate`) |
| Trabajo asíncrono / programado | `<app>/tasks.py` → skill `ponteglam-backend-celery` |
| Notificar a un usuario | `notifications` → skill `ponteglam-backend-notifications` |
| Lógica de citas | `services` → skill `ponteglam-backend-appointments` |
| Estado / tipo configurable | Fila de `core.Type` en una `core.Category` → skill `ponteglam-backend-core` |
| Utilidad compartida | `core/utils.py`, `core/permissions.py`, `core/validators.py` |
| Script temporal o de prueba | `antigravity/` (borrarlo al terminar) |

## Infraestructura

- **Base de datos**: PostgreSQL (`POSTGRES_*` en `.env`).
- **Redis**: db 0 = broker de Celery (`REDIS_URL`); db 1 = caché de Django (`REDIS_CACHE_URL`). La caché es Redis real: el throttle de login y la caché de listados dependen de ella.
- **Celery**: worker + beat. Resultados en BD (`django-db`, ver admin → Task results).
- **Channels**: `ASGI_APPLICATION`, capa **InMemory** (no escala entre procesos). Auth de WebSocket con `ponteglam/middleware.py:TokenAuthMiddleware` (header `Authorization: Token <key>`).
- **Firebase**: `firebase_admin` se inicializa en `settings.py` con el JSON de service account de la raíz. `fcm_django` guarda los dispositivos.
- **Correo**: SMTP Gmail (`EMAIL`, `PASSWORD` en `.env`), enviado siempre desde Celery.
- **Media**: `MEDIA_ROOT = ../media` (fuera del repo), servido por Django en DEBUG.
- **Proxy HTTPS**: `SECURE_PROXY_SSL_HEADER` confía en `X-Forwarded-Proto` (ngrok y nginx lo envían) para que las URLs absolutas salgan en `https`.

## Comandos

```bash
env/bin/python manage.py runserver 0.0.0.0:8000
env/bin/celery -A ponteglam worker --loglevel=info
env/bin/celery -A ponteglam beat --loglevel=info
env/bin/python manage.py makemigrations && env/bin/python manage.py migrate
env/bin/python manage.py shell < core/scripts/create_default_settings.py   # semillas
env/bin/python -m pytest <app>/tests.py -q
```

**Después de cambiar código de tareas o settings hay que reiniciar el worker de Celery**;
`runserver` se recarga solo, Celery no.

## Reglas obligatorias (resumen de GEMINI.md / GEMINI_WORKFLOW.md)

1. Sin comentarios obvios; docstrings describen el propósito. Comentar solo el "por qué".
2. Imports al tope (stdlib → Django → terceros → locales). Nada de imports dentro de funciones en código nuevo.
3. `.env`, `*.key`, `*.pem`, JSON de Firebase, `credentials`: **preguntar antes de leerlos**.
4. OWASP: ORM siempre, `permission_classes` explícitos, no loguear tokens/contraseñas/PII.
5. MTV estricto: vistas delgadas, queries en managers, validación en serializers.
6. Archivos temporales solo en `antigravity/` y se borran al terminar.
7. Git: nada de `commit`/`push` sin autorización explícita.
8. Fechas: BD en UTC, `timezone.now()` siempre, nunca `datetime.now()`; conversión a hora local con `core.utils.get_local_time` / `now_in_tz` usando `settings.TIME_ZONE`.

## Deuda conocida (no copiar estos patrones en código nuevo)

- Hay imports dentro de funciones (`core/utils.py`, `core/permissions.py`, vistas de `services`) y `print()` en vistas. En código nuevo: imports arriba y `logging`.
- Muchas vistas de `services/api/views.py` tienen lógica de negocio inline (más de 1400 líneas). Al tocarlas, extraer a managers o funciones de servicio si el cambio lo justifica, sin reescribir lo que no se toca.
- `GEMINI.md` menciona un campo `timezone` en "HeadquarterCompany": **no existe**. Usar `settings.TIME_ZONE`.
- `Company.is_verified` existe en la BD pero no está declarado en `companies/models.py` (parche con default en Postgres).
- `SECRET_KEY` y `DEBUG=True` están en el código; no replicar en settings nuevos.
- Los tests de `services/tests.py` usan el fixture `mocker` y `pytest-mock` no está instalado.

## Skills relacionadas

`ponteglam-backend-core`, `ponteglam-backend-api-endpoints`, `ponteglam-backend-celery`,
`ponteglam-backend-notifications`, `ponteglam-backend-appointments`, `ponteglam-api-contract`.
