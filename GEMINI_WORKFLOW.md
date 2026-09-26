# 🔐 Reglas de Seguridad y Flujo de Trabajo — Django AI Assistant

> Complemento de las reglas base. Aplica en conjunto con `GEMINI.md`.
> Enfocado en patrones de calidad, flujo de trabajo seguro y buenas prácticas avanzadas.

---

## 1. Calidad de Código — Comentarios con Propósito

### Lo que NUNCA debe aparecer en el código generado

```python
# ❌ Comentarios de relleno
x = x + 1  # Incrementamos x en 1
user.save()  # Guardamos el usuario
return HttpResponse("OK")  # Retornamos respuesta

# ❌ Placeholders vacíos
def calcular_descuento(precio):
    # Your code here
    pass

# ❌ Comentarios de sección sin valor
# ============== INICIO ==============
# ... código ...
# ============== FIN ================
```

### Lo que SÍ debe documentarse

```python
# ✅ Explica el "por qué", no el "qué"
# Usamos select_related aquí para evitar N+1 queries en la vista de listado
orders = Order.objects.select_related('customer', 'product').filter(status='pending')

# ✅ Documenta decisiones no obvias
# Django no lanza excepción al llamar delete() en un queryset vacío,
# pero sí al llamar .get() sin resultado — usamos filter().first() intencionalmente
instance = MyModel.objects.filter(pk=pk).first()
```

---

## 2. Importaciones — Estructura y Orden Canónico

### Orden obligatorio (PEP 8 + Django convention)

```python
# 1. Librería estándar
import os
import json
from datetime import datetime, timedelta
from typing import Optional

# 2. Django core
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.conf import settings

# 3. Librerías de terceros
import stripe
from rest_framework import serializers
from celery import shared_task

# 4. Apps locales del proyecto
from apps.orders.models import Order
from apps.users.services import send_welcome_email
from core.utils import paginate_queryset
```

### Reglas adicionales

- No usar `from module import *` — siempre importar explícitamente.
- Las importaciones relativas (`.models`, `..utils`) son aceptables dentro de una misma app.
- Si una importación circular existe, resolverla con inyección de dependencias o restructurando el código — nunca con imports dentro de funciones como workaround permanente.

---

## 3. Archivos Sensibles — Protocolo de Seguridad Completo

### Archivos que requieren confirmación previa

| Archivo | Razón |
|---|---|
| `.env`, `.env.*` | Credenciales, claves secretas |
| `settings/production.py` | Configuración de producción |
| `*.pem`, `*.key`, `*.crt` | Certificados SSL/TLS |
| `credentials.json`, `secrets.json` | Tokens de servicios externos |
| `database.yml`, `pg_service.conf` | Credenciales de base de datos |

### Flujo de confirmación obligatorio

```
Asistente: "Necesito revisar `.env` para verificar la configuración de la BD.
            Este archivo puede contener credenciales sensibles.
            ¿Confirmas que debo acceder a él? (sí/no)"

Desarrollador: "sí"  ← solo entonces procede
```

### Buenas prácticas que el asistente debe reforzar

```python
# ❌ Nunca generar código con valores hardcodeados
DATABASES = {
    'default': {
        'PASSWORD': 'mi_password_secreto',
    }
}

# ✅ Siempre referenciar desde el entorno
import environ
env = environ.Env()
DATABASES = {
    'default': env.db('DATABASE_URL')
}
```

---

## 4. OWASP — Checklists por Tipo de Componente

### Al crear una Vista (View)

- [ ] ¿Tiene control de acceso? (`@login_required` o `LoginRequiredMixin`)
- [ ] ¿Los permisos están verificados? (`@permission_required` o `has_perm`)
- [ ] ¿Las entradas del usuario pasan por un Form/Serializer antes de usarse?
- [ ] ¿No hay SQL crudo con interpolación de strings?
- [ ] ¿Los errores no exponen stack traces al usuario final?

### Al crear un Model

- [ ] ¿Los campos de contraseña usan `make_password()` / `set_password()`?
- [ ] ¿Los campos con datos sensibles tienen `editable=False` donde corresponde?
- [ ] ¿Se usan `validators` de Django para validar formatos?

### Al crear un Template

- [ ] ¿No se usa `| safe` sobre datos de entrada del usuario?
- [ ] ¿Los formularios POST tienen `{% csrf_token %}`?
- [ ] ¿Las URLs externas son validadas antes de renderizarse?

### Al crear una API (DRF)

- [ ] ¿Los serializers validan todos los campos de entrada?
- [ ] ¿Los endpoints tienen `permission_classes` explícitos?
- [ ] ¿Se usa throttling para endpoints públicos o de autenticación?
- [ ] ¿La paginación está activada para listados?

---

## 5. Estructura Django — Patrones Obligatorios

### Organización de apps

```
proyecto/
├── apps/
│   ├── users/          ← gestión de usuarios
│   ├── orders/         ← lógica de pedidos
│   └── notifications/  ← envío de mensajes
├── core/               ← utilidades compartidas, middleware, base models
├── config/             ← settings/, urls.py raíz, wsgi.py, asgi.py
├── antigravity/        ← archivos temporales del asistente (ver Regla 6)
├── templates/
├── static/
└── manage.py
```

### Dónde vive cada pieza de lógica

| Tipo de lógica | Dónde va |
|---|---|
| Reglas de negocio complejas | `services.py` dentro de la app |
| Queries reutilizables | `managers.py` o `querysets.py` |
| Validación de datos de entrada | `forms.py` o `serializers.py` |
| Lógica de presentación | `templatetags/` o propiedades del modelo |
| Tareas asíncronas | `tasks.py` (Celery) |
| Señales | `signals.py` (conectadas en `apps.py`, no en `models.py`) |

---

## 6. Carpeta `antigravity/` — Reglas de Uso

### Propósito
Espacio aislado para que el asistente trabaje sin contaminar el código de producción.

### Qué puede ir aquí
- Scripts de prueba de queries o lógica
- Archivos de datos semilla temporales
- Prototipos de funciones antes de ubicarlas correctamente
- Outputs de depuración

### Ciclo de vida obligatorio

```
1. Asistente crea archivo en antigravity/
2. Usa el archivo para desarrollar / probar
3. Integra la solución al código real
4. ELIMINA el archivo de antigravity/ ✅
```

### Lo que NO puede ir en `antigravity/`
- Código que vaya a ejecutarse en producción
- Migraciones de Django
- Configuraciones de settings
- Archivos con credenciales reales

---

## 7. Git — Control de Cambios Asistido

### Comandos que el asistente puede ejecutar libremente
```bash
git status
git log --oneline -10
git diff
git diff --staged
git branch
```

### Comandos que requieren confirmación explícita del desarrollador
```bash
git add .              # ← requiere "sí, agrega los cambios"
git commit -m "..."    # ← requiere aprobación del mensaje
git push               # ← requiere "sí, sube al repositorio"
git push --force       # ← NUNCA sin autorización doble
git merge              # ← requiere confirmación
git rebase             # ← requiere confirmación
git tag                # ← requiere confirmación
```

### Formato de mensajes de commit sugerido (Conventional Commits)

```
feat: agrega autenticación con JWT
fix: corrige validación de email en registro
refactor: extrae lógica de descuento a OrderService
docs: actualiza README con instrucciones de despliegue
test: agrega pruebas unitarias para OrderManager
chore: actualiza dependencias a versiones seguras
```

### Flujo de aprobación

```
Asistente: "Los siguientes archivos están listos para commit:
  - apps/orders/models.py  (nuevo modelo OrderItem)
  - apps/orders/serializers.py  (serializer actualizado)
  
  Mensaje sugerido: 'feat: agrega modelo OrderItem con relación a Order'
  
  ¿Procedo con el commit y push a origin/main?"

Desarrollador: "sí, procede" ← commit ejecutado
```

---

## Resumen Rápido de Reglas

| # | Regla | Acción por defecto |
|---|---|---|
| 1 | Comentarios | Solo documentar lógica no obvia |
| 2 | Importaciones | Siempre al tope, orden PEP 8 |
| 3 | Archivos `.env` | Preguntar antes de acceder |
| 4 | Seguridad OWASP | Aplicar checklist por componente |
| 5 | Modelo Django | MTV + Services + Managers |
| 6 | Temporales | Solo en `antigravity/`, limpiar al final |
| 7 | Git push | Solo con autorización explícita |
