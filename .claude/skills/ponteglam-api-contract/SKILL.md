---
name: ponteglam-api-contract
description: Contrato entre el backend Django y el app Flutter de PonteGlam — sobre de respuesta success/error/detail, autenticación por Token, formato de fechas, paginación, URLs de imágenes, códigos de catálogo y payload de notificaciones. Úsala siempre que un cambio cruce la frontera API (nuevo endpoint, cambio de respuesta, nuevo campo, nuevo go_to) para mantener backend y app sincronizados. Existe una copia idéntica en ponteglam_backend y ponteglam_mobile; si cambias una, cambia la otra.
---

# Contrato API backend ↔ app

Repos: `ponteglam_backend` (Django) y `ponteglam_mobile` (Flutter). Base URL del app:
`EndPoints.baseUrl` en `lib/config/constant/end_point_constant.dart`
(hoy el dominio fijo de ngrok `https://scarlet-automorphic-scripturally.ngrok-free.dev`).

## Autenticación

- Login: `POST /api-token-auth/` (`username`, `password`) → `{"success": "...", "user": {..., "token": "<key>"}}`.
- Requests autenticadas: header `Authorization: Token <key>`. El app guarda el token en
  `IStorage` (secure storage) con la llave `keyAuthToken`.
- WebSocket: el mismo header en el handshake (`TokenAuthMiddleware`).

## Sobre de respuesta

| Llave raíz | Significado | Cómo lo trata el app |
|---|---|---|
| `success` | Datos o mensaje de éxito | `response.data[keySuccess]` → modelo |
| `error` | Error de cliente/negocio (string o dict de serializer) | `throwClientResponse(status, data['error'])` → `Failure` |
| `detail` | Mensaje para mostrar tal cual (reglas de negocio, errores DRF) | `throwServerResponse(status, data['detail'])` |
| `count/next/previous/results` | Listado paginado (15 por página) | El datasource lee `results` |

Reglas:
- Una respuesta tiene **una** de `success` / `error` / `detail`. No agregar llaves hermanas
  nuevas en la raíz sin actualizar el datasource del app.
- El cliente Dio usa `validateStatus: (_) => true`: **no lanza** por 4xx/5xx. El datasource decide
  por llaves + `statusCode`. Un 200 sin `success` rompe el parseo.
- Mensajes para el usuario en español.

## Datos

- Fechas: ISO 8601 con offset. Salida del backend `%Y-%m-%dT%H:%M:%S%z`, almacenadas en UTC.
  El app convierte con `AppDateUtils.fromUtc(...)` antes de mostrar y envía fechas con offset.
- Dinero: `DecimalField` serializado como string o número; el app formatea con `CurrencyUtils` / `FormatCurrencyUtil`.
- Imágenes: URL absoluta construida con el host de la request (`https`, gracias a
  `SECURE_PROXY_SSL_HEADER`). El app **siempre** pasa por `ImageUrlHelper.resolve(url)`, que
  reescribe el host al `baseUrl` actual.
- Catálogos (`core.Type`): el app recibe y compara **códigos** (`available`, `profile_image`,
  `gender_service`…). Renombrar un código es un cambio incompatible.
- Ids: enteros. En payloads FCM viajan como string.

## Notificaciones push

`data = {"action" | "go_to": <destino>, "appointment_id": "<id>", "prompt_rating"?: "true"}`.
Destinos que el app maneja: `history`, `client_appointments`, `appointment_detail`,
`supplier_appointments`. Agregar uno nuevo requiere cambios en el app
(`notification_handler.dart`, `cloud_messaging.dart`, `local_notification_service.dart`).

## Checklist de cambio que cruza la frontera

1. Backend: vista + router + serializer con el sobre correcto.
2. App: constante en `EndPoints` (getter `String get <nombre>Url => "$baseUrl/<app>/api/<ruta>/";`).
3. App: datasource abstracto + implementación, modelo con `fromJson` tolerante (`?? default`).
4. Parámetros nuevos **opcionales y con default compatible**: los APKs ya instalados siguen llamando sin ellos.
5. Si cambia la respuesta de un endpoint existente, recordar que los APKs viejos no se actualizan solos: preferir campos nuevos a campos renombrados.
6. Recompilar el APK solo si cambió el app (`flutter build apk --debug`).
