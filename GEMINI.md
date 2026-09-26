# 🧠 Reglas de Desarrollo — Proyecto Django

> Estas reglas aplican a todo el desarrollo asistido por IA en este proyecto.
> Deben seguirse **sin excepción** en cada sesión de trabajo.

---

## 1. Código Limpio — Sin Comentarios Innecesarios

- **No agregar comentarios** sobre código que se entiende por sí solo.
  - ❌ `# Retorna el usuario` sobre `return user`
  - ❌ `# Tu código aquí` / `# Your code here`
  - ❌ `# Iteramos sobre la lista` sobre `for item in items:`
- **Sí agregar comentarios** cuando la lógica es no obvia, documenta una decisión de diseño, o explica un comportamiento inesperado del sistema.
- Los docstrings en funciones y clases deben describir el **propósito**, no la implementación.

```python
# ❌ Mal
def get_active_users():
    # Filtramos los usuarios activos
    return User.objects.filter(is_active=True)  # Retornamos el queryset

# ✅ Bien
def get_active_users():
    """Retorna todos los usuarios con cuenta activa."""
    return User.objects.filter(is_active=True)
```

---

## 2. Importaciones al Tope del Archivo

- **Todas las importaciones** deben estar en la parte superior del archivo, nunca dentro de funciones, métodos o bloques condicionales.
- Orden recomendado (PEP 8):
  1. Librería estándar de Python
  2. Librerías de terceros (Django, DRF, etc.)
  3. Importaciones locales del proyecto

```python
# ❌ Mal
def process_payment(data):
    import stripe
    from myapp.models import Order
    ...

# ✅ Bien
import stripe
from myapp.models import Order

def process_payment(data):
    ...
```

- **Excepción permitida**: importaciones condicionales para compatibilidad de versiones (`TYPE_CHECKING`), siempre documentadas.

---

## 3. Archivos Privados — Política de No Acceso sin Confirmación

- El asistente **NO debe leer, editar, mostrar ni referenciar** el contenido de los siguientes archivos sin preguntar primero al desarrollador:
  - `.env` y cualquier variante (`.env.local`, `.env.production`, `.env.staging`)
  - `secrets.json`, `credentials.json`
  - Archivos de certificados (`.pem`, `.key`, `.crt`)
  - Configuraciones con contraseñas o tokens hardcodeados

- **Protocolo**: antes de cualquier acción sobre estos archivos, el asistente debe preguntar:
  > "Este archivo puede contener información sensible. ¿Confirmas que quieres que lo revise?"

- Para variables de entorno, usar siempre `os.environ.get('VAR')` o `django-environ` — nunca valores literales en el código.

---

## 4. Seguridad OWASP — Principios Obligatorios

Este proyecto respeta el [OWASP Top 10](https://owasp.org/Top10/). El asistente debe aplicar las siguientes reglas en todo código generado:

| Riesgo OWASP | Regla obligatoria |
|---|---|
| Inyección (A03) | Usar ORM de Django siempre. Nunca SQL crudo con interpolación de strings. |
| Autenticación rota (A07) | Usar `django.contrib.auth`. No implementar autenticación propia sin justificación. |
| Datos sensibles expuestos (A02) | No loguear contraseñas, tokens ni PII. Usar HTTPS. |
| Control de acceso (A01) | Decoradores `@login_required`, `@permission_required`, o `PermissionMixin` en cada vista. |
| CSRF (A01 / configuración) | No desactivar `CsrfViewMiddleware`. Usar `{% csrf_token %}` en formularios. |
| Configuración incorrecta (A05) | `DEBUG=False` en producción. `SECRET_KEY` desde variable de entorno. |
| Componentes vulnerables (A06) | No agregar dependencias sin revisar su versión y mantenimiento. |
| XSS (A03) | No usar `mark_safe()` ni `| safe` en templates sin sanitización explícita. |

```python
# ❌ Inyección SQL — nunca hacer esto
User.objects.raw(f"SELECT * FROM users WHERE name = '{nombre}'")

# ✅ ORM seguro
User.objects.filter(username=nombre)
```

---

## 5. Respetar el Modelo de Django (MTV)

- **Models**: lógica de negocio y acceso a datos vive en los modelos o managers. No en las vistas.
- **Templates**: solo presentación. Sin lógica de negocio.
- **Views**: coordinan la petición → modelo → template. Delgadas por diseño.
- **Forms / Serializers**: validación de entrada. Nunca validar manualmente en la vista lo que un Form puede hacer.
- **URLs**: definidas en `urls.py`, con nombres (`name=`) para usar `reverse()` / `{% url %}`.
- **Apps**: cada funcionalidad cohesiva en su propia app Django. No poner todo en una sola app.
- **Managers**: queries complejas o reutilizables deben vivir en un `Manager` personalizado, no inline en las vistas.

```python
# ❌ Lógica de negocio en la vista
def dashboard(request):
    users = User.objects.filter(is_active=True, date_joined__year=2024)
    revenue = sum(o.total for o in Order.objects.filter(status='paid'))
    ...

# ✅ Lógica en el modelo / manager
class OrderManager(models.Manager):
    def total_revenue(self):
        return self.filter(status='paid').aggregate(total=Sum('amount'))['total']
```

---

## 6. Archivos Temporales → Carpeta `antigravity/`

- Si el asistente necesita crear archivos para **pruebas, scripts de exploración, datos de muestra o ejecuciones temporales** durante el desarrollo, **debe crearlos en la carpeta `antigravity/`**.
- Esta carpeta actúa como sandbox de desarrollo. Su contenido no debe llegar a producción.
- **Regla de limpieza**: todo archivo creado en `antigravity/` que ya no sea necesario para el plan de implementación **debe eliminarse** antes de cerrar la tarea.
- El asistente **no debe crear archivos temporales en** `apps/`, `templates/`, `static/`, ni en el raíz del proyecto.

```
proyecto/
├── antigravity/          ← archivos temporales, scripts de prueba
│   ├── test_query.py     (se elimina al terminar)
│   └── seed_data.json    (se elimina al terminar)
├── myapp/
├── manage.py
└── ...
```

---

## 7. Git — No Subir Código sin Autorización Explícita

- El asistente **no ejecutará** ningún comando de git que modifique el repositorio remoto (`git push`, `git push --force`, `git push origin`, etc.) sin que el desarrollador lo autorice explícitamente en la conversación.
- Comandos de lectura (`git status`, `git log`, `git diff`) son permitidos libremente.
- Antes de cualquier `git add` + `git commit` + `git push`, el asistente debe mostrar un resumen de los cambios y esperar confirmación.
- **Nunca** crear ramas, tags ni releases de forma autónoma.

```
# El asistente puede sugerir:
git add apps/myapp/models.py
git commit -m "feat: agrega modelo de Pedido con validaciones"
git push origin main

# Pero NO ejecutará estos comandos hasta recibir: "sí, procede" o equivalente.
```
## 8. Zona horaria y manejo de fechas

### Regla fundamental
La base de datos almacena SIEMPRE en UTC.
La conversión a hora local ocurre solo cuando se necesita
lógica por hora local o al construir mensajes para el usuario.
Nunca almacenar fechas en hora local de Colombia.

### Configuración requerida en settings.py
  TIME_ZONE = env('APP_TIMEZONE', default='America/Bogota')
  USE_TZ = True   ← obligatorio, nunca cambiar a False

### Variable de entorno requerida en .env
  APP_TIMEZONE=America/Bogota

### Reglas obligatorias

1. Siempre usar timezone.now() de django.utils.
   Nunca usar datetime.datetime.now() ni datetime.datetime.today()
   - BIEN: from django.utils import timezone / timezone.now()
   - MAL:  from datetime import datetime / datetime.now()

2. Los modelos con fecha automática deben usar:
   - BIEN: created_at = models.DateTimeField(auto_now_add=True)
   - BIEN: updated_at = models.DateTimeField(auto_now=True)
   - BIEN: field = models.DateTimeField(default=timezone.now)
   - MAL:  field = models.DateTimeField(default=datetime.now)

3. Nunca crear objetos datetime sin zona horaria (naive).
   - BIEN: timezone.now()
   - MAL:  datetime(2026, 4, 14, 15, 0, 0)  ← naive, sin tz

4. Para lógica que depende de la hora local de Colombia
   (por ejemplo: ¿esta cita es hoy? ¿ya pasó el plazo?):
   Convertir a local primero usando get_local_time() de
   core/utils.py. Nunca comparar UTC con hora local.

5. Para notificaciones, emails o mensajes al usuario
   que incluyan hora: convertir siempre a local antes
   de construir el mensaje.

6. Nunca hardcodear 'America/Bogota' en vistas, modelos
   o tareas. Usar settings.TIME_ZONE o el campo timezone
   del modelo HeadquarterCompany.

### Utilidades centralizadas
Toda lógica de conversión pasa por:
core/utils.py

  get_local_time(dt, tz_name)
    Convierte un datetime UTC al timezone indicado.
    Usar para lógica de negocio y mensajes al usuario.

  now_in_tz(tz_name)
    Retorna timezone.now() convertido al timezone indicado.
    Usar cuando necesitas la hora actual en Colombia.

### Ejemplo correcto — lógica por hora local
  from core.utils import get_local_time, now_in_tz

  local_now = now_in_tz(settings.TIME_ZONE)
  appt_local = get_local_time(
      appointment.start_time,
      appointment.headquarter_place.timezone
  )
  is_today = local_now.date() == appt_local.date()  ✅

### Ejemplo incorrecto — NO hacer esto
  now = timezone.now()
  is_today = now.date() == appointment.start_time.date()
  # ❌ Compara fechas UTC. A las 8PM en Colombia
  #    UTC ya es el día siguiente. Falla para citas nocturnas.

### Ejemplo correcto — mensaje con hora al usuario
  local_time = get_local_time(
      appointment.start_time,
      appointment.headquarter_place.timezone
  )
  msg = f"Tu cita es a las {local_time.strftime('%I:%M %p')}"
  # Resultado: "Tu cita es a las 03:00 PM" ✅

### Ejemplo incorrecto — NO hacer esto
  msg = f"Tu cita es a las {appointment.start_time.strftime('%H:%M')}"
  # Resultado: "Tu cita es a las 20:00" ❌ (muestra UTC)

### Verificación rápida en shell
  python manage.py shell
  >>> from django.utils import timezone
  >>> timezone.now()
  # Muestra UTC — correcto, así se guarda en BD
  >>> timezone.localtime()
  # Muestra hora Colombia (UTC−5) — correcto para mostrar

### Cambiar zona horaria
Para migrar a otra zona o soportar múltiples zonas:
1. Cambiar APP_TIMEZONE en .env
2. El campo timezone en HeadquarterCompany ya soporta
   zonas por sede sin cambios adicionales en el código
3. La BD no requiere migración porque siempre guarda UTC