# Backend > Frontend: contrato de endpoints

Para Marcos. Ejemplos completos de request/response en
`postman_collection.json`, en esta misma carpeta - este documento es el mapa,
no el detalle de cada payload.

---

## Entorno `dev` (AWS, cuenta personal, temporal)

**Estado destruido.** Los valores de abajo son del último
despliegue y ya no responden, te los dejo de muestra:

```
Base URL:        https://3exbh6sz27.execute-api.eu-west-1.amazonaws.com  (muerto)
Cognito Pool ID: eu-west-1_1nHy5snnV                                     (muerto)
App Client CLIENTE:    96iets4j65uuusssbm76mdo8v
App Client GUARDERIA:  36457etqg28poief3ug8tfpbh8
App Client ADMIN:      2omoqa06q09pisf9mar0qnqkk1
```

---

## Autenticación

Registro y login **van directos contra Cognito**, no contra esta API (usar el
SDK de Amplify/Cognito Identity con el App Client que corresponda según el
formulario: adoptante > `CLIENTE`, protectora > `GUARDERIA`). El panel de
administración no tiene registro propio: el usuario ADMIN se crea a mano.

Tras el login, mandar el `IdToken` (no el `AccessToken`) en cada petición a una
ruta privada:

```
Authorization: Bearer <IdToken>
```

Sin ese header, cualquier ruta privada responde `401`. Con el grupo
equivocado, `403`.

---

## Endpoints

| Método y ruta | Auth | Qué hace |
|---|---|---|
| `GET /animales` | pública | Lista animales. Query params: `estado`, `tipo`, `edad` |
| `GET /animales/{id}` | pública | Ficha de un animal. `404` si no existe |
| `GET /guarderias` | pública | Lista guarderías aprobadas |
| `POST /solicitudes` | pública | Formulario de interés anónimo (nombre, email, teléfono, mensaje) |
| `GET /cliente/perfil` | JWT, grupo `CLIENTE` | Perfil del cliente logueado |
| `PUT /cliente/perfil` | JWT, grupo `CLIENTE` | Actualiza nombre/teléfono/descripción |
| `GET /cliente/solicitudes` | JWT, grupo `CLIENTE` | Historial de solicitudes propias |
| `POST /cliente/solicitudes` | JWT, grupo `CLIENTE` | Solicitud con sesión (usa el perfil, no repite datos) |
| `DELETE /cliente` | JWT, grupo `CLIENTE` | Borra la cuenta: solicitudes, perfil y el usuario de Cognito |
| `PUT /guarderia/perfil` | JWT, grupo `GUARDERIA` | Actualiza nombre/teléfono/ciudad/provincia/descripción de la propia guardería |
| `POST /guarderias/{guarderia_id}/animales` | JWT, grupo `GUARDERIA` | Publica un animal (sin `fotos`, ver más abajo). `guarderia_id` debe ser el propio `sub`; `403` si no está aprobada |
| `PUT /guarderias/{guarderia_id}/animales/{animal_id}` | JWT, grupo `GUARDERIA` | Edita un animal propio (incluye cambiar `estado`: disponible/no_disponible/en_proceso/adoptado). Tampoco lleva `fotos` |
| `POST /guarderias/{guarderia_id}/animales/{animal_id}/fotos` | JWT, grupo `GUARDERIA` | Pide una presignada de subida (ver sección "Fotos" más abajo). `409` si el animal ya tiene 5 |
| `DELETE /guarderias/{guarderia_id}/animales/{animal_id}` | JWT, grupo `GUARDERIA` | Elimina un animal propio (y sus fotos en S3) |
| `GET /guarderias/{guarderia_id}/solicitudes` | JWT, grupo `GUARDERIA` | Solicitudes recibidas sobre los animales propios |
| `POST /guarderias/{guarderia_id}/solicitudes/{animal_id}/aceptar` | JWT, grupo `GUARDERIA` | Acepta una solicitud (query param `fecha`, viene en la respuesta de la solicitud). Pone el animal en `en_proceso` |
| `POST /guarderias/{guarderia_id}/solicitudes/{animal_id}/rechazar` | JWT, grupo `GUARDERIA` | Rechaza una solicitud (query param `fecha`). Si era anónima se borra el ítem entero; si tenía cuenta se le borran los datos de contacto y se conserva en el historial del cliente |
| `GET /admin/guarderias/pendientes` | JWT, grupo `ADMIN` | Panel de aprobación |
| `POST /admin/guarderias/{sub}/aprobar` | JWT, grupo `ADMIN` | Aprueba una guardería |
| `POST /admin/guarderias/{sub}/rechazar` | JWT, grupo `ADMIN` | Rechaza con motivo (`{"motivo": "..."}`) |

**Aceptar/rechazar solicitud, en detalle:** `fecha` identifica la solicitud
concreta sobre ese animal (puede haber varias) y es exactamente el string que
devuelve el campo `fecha` al crear o listar una solicitud, se manda tal cual,
como query param, sin reformatear. Devuelven `409` si la solicitud ya no está
`pendiente` (alguien se adelantó).

**Todas las rutas responden `422`** con el detalle de Pydantic si falta un
campo o el tipo no cuadra - útil para validar formularios sin esperar al
backend.

---

## Enlaces de decisión por correo: nada que hacer en el frontend

`POST /solicitudes` y `POST /cliente/solicitudes` ahora envían un correo real
por SES a la guardería, con dos enlaces (aceptar/rechazar) que abren una
página de confirmación **servida por el propio backend** (`GET/POST
/decision`, sin JWT, token de un solo uso en la URL). El frontend no llama a
estas rutas ni las enlaza desde ningún sitio: solo existen dentro del correo.
La guardería puede seguir haciendo lo mismo desde su panel
(`POST .../aceptar` y `.../rechazar`), que no cambian.

## Fotos: cambio de contrato importante

`Animal.fotos` **ya no son URLs** (ni de ejemplo ni reales): ahora es una
lista de **ids de foto** (`fotoId`, un uuid), y **no hay ninguna URL pública
que el frontend pueda usar todavía** - falta CloudFront delante del bucket de
derivadas (fase pendiente, mismo motivo que el catálogo). No hay nada que
mostrar en `<img src>` por ahora; tratar `fotos` como "cuántas fotos tiene y
con qué id", no como enlaces.

Flujo de subida (todo esto en el navegador, la API no recibe el fichero):

1. `POST /guarderias/{guarderia_id}/animales/{animal_id}/fotos` con
   `{"contentType": "image/jpeg"|"image/png"|"image/webp"}` > devuelve
   `{"fotoId": "...", "url": "...", "fields": {...}}`.
2. El navegador hace un `POST` **multipart/form-data** directo a `url`, con
   todos los `fields` devueltos como campos del formulario **antes** que el
   campo `file` (S3 lo exige en ese orden), y el fichero en el campo `file`.
   Tamaño entre 10 KB y 8 MB, caduca a los 5 minutos.
3. El procesado (miniatura 400px + ficha 1200px, sin EXIF) es asíncrono: no
   hay forma de saber desde el frontend cuándo terminó salvo volver a pedir
   el animal y comprobar si `fotos` ya incluye el `fotoId` devuelto en el
   paso 1. Si el fichero subido no era una imagen de verdad, nunca aparecerá
   (se borra en silencio).

Máximo 5 fotos por animal (`409` si ya las tiene). Al borrar el animal se
borran también sus fotos en S3.

## Lo que todavía no existe (no diseñar el frontend contra esto)

CloudFront/WAF (es lo que haría públicas las fotos y el catálogo), CI/CD.

**Nota sobre el catálogo:** por debajo ya existe un catálogo JSON precalculado
en S3 que se regenera solo (Streams + Lambda), pero el bucket es **privado**
(sin CloudFront/OAC todavía), el frontend sigue usando `GET /animales` y
`GET /guarderias` tal cual, no hay nada que cambiar ahí todavía. Cuando exista
CloudFront, esos dos endpoints se sustituirán por leer `/data/manifest.json` y
`/data/catalogo-<hash>.json` directamente, sin pasar por la API.
