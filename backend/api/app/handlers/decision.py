"""
"""
import base64
import logging
from datetime import datetime
from html import escape
from urllib.parse import parse_qs

from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.repositorio_solicitudes import SolicitudYaProcesadaError
from app.core.respuestas import CORS_HEADERS
from app.core.tokens import verificar_token
from app.models.solicitud import EstadoSolicitud, Solicitud
from app.services.decisiones import aplicar_decision

logger = logging.getLogger(__name__)

_ACCIONES = {"aceptar", "rechazar"}
_ETIQUETA_ACCION = {"aceptar": "Aceptar", "rechazar": "Rechazar"}


def _pagina(titulo: str, cuerpo: str) -> str:
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 32rem; margin: 3rem auto; padding: 0 1rem; color: #222; }}
button {{ font-size: 1rem; padding: 0.6rem 1.2rem; cursor: pointer; }}
dl {{ display: grid; grid-template-columns: auto 1fr; gap: 0.25rem 1rem; }}
dt {{ font-weight: 600; }}
</style></head>
<body><h1>{titulo}</h1>{cuerpo}</body></html>"""


def _html_response(titulo: str, cuerpo: str, status_code: int) -> dict:
    return {
        "statusCode": status_code,
        "headers": {**CORS_HEADERS, "Content-Type": "text/html; charset=utf-8"},
        "body": _pagina(titulo, cuerpo),
    }


def _mensaje(titulo: str, texto: str, estado_http: int) -> dict:
    return _html_response(titulo, f"<p>{texto}</p>", estado_http)


def _solicitud_valida(animal_id: str, fecha: str, token: str) -> Solicitud | None:
    """None si la solicitud no existe, ya se resolvió, el token no
    corresponde o caducó. No distingue el motivo en el valor de retorno"""
    solicitud = repo_solicitudes.obtener_solicitud(animal_id, fecha)
    if solicitud is None or solicitud.estado != EstadoSolicitud.pendiente:
        return None
    if solicitud.tokenHash is None or solicitud.tokenExpira is None:
        return None
    if datetime.utcnow() > solicitud.tokenExpira:
        return None
    if not verificar_token(token, solicitud.tokenHash):
        logger.warning("TOKEN_INVALIDO intento de decisión con token inválido para animalId=%s fecha=%s", animal_id, fecha)
        return None
    return solicitud


def _mostrar_confirmacion(event: dict) -> dict:
    query = event.get("queryStringParameters") or {}
    animal_id, fecha, token, accion = query.get("animalId"), query.get("fecha"), query.get("token"), query.get("accion")
    if not all([animal_id, fecha, token, accion]) or accion not in _ACCIONES:
        return _mensaje("Petición no válida", "Faltan parámetros o la acción no es válida.", 422)

    solicitud = repo_solicitudes.obtener_solicitud(animal_id, fecha)
    if solicitud is None:
        return _mensaje("Solicitud no encontrada", "Esta solicitud no existe o ya fue eliminada.", 404)
    if solicitud.estado != EstadoSolicitud.pendiente:
        return _mensaje("Solicitud ya resuelta", "Esta solicitud ya fue aceptada o rechazada anteriormente.", 410)
    if _solicitud_valida(animal_id, fecha, token) is None:
        return _mensaje("Enlace no válido", "Este enlace no es válido o ha caducado.", 403)

    # Todo lo interpolado abajo es controlado por quien envió la solicitud (o
    # por la query string del enlace) y nunca debe insertarse sin escapar.
    cuerpo = f"""
    <dl>
      <dt>Adoptante</dt><dd>{escape(solicitud.nombre or "")}</dd>
      <dt>Mensaje</dt><dd>{escape(solicitud.mensaje or "")}</dd>
    </dl>
    <p>¿Confirmas que quieres <strong>{_ETIQUETA_ACCION[accion].lower()}</strong> esta solicitud?</p>
    <form method="post" action="/decision">
      <input type="hidden" name="animalId" value="{escape(animal_id)}">
      <input type="hidden" name="fecha" value="{escape(fecha)}">
      <input type="hidden" name="token" value="{escape(token)}">
      <input type="hidden" name="accion" value="{escape(accion)}">
      <button type="submit">{_ETIQUETA_ACCION[accion]} solicitud</button>
    </form>
    """
    return _html_response("Confirmar decisión", cuerpo, 200)


def _confirmar_decision(event: dict) -> dict:
    cuerpo_crudo = event.get("body") or ""
    if event.get("isBase64Encoded"):
        cuerpo_crudo = base64.b64decode(cuerpo_crudo).decode()
    campos = {clave: valores[0] for clave, valores in parse_qs(cuerpo_crudo).items()}
    animal_id, fecha, token, accion = campos.get("animalId"), campos.get("fecha"), campos.get("token"), campos.get("accion")
    if not all([animal_id, fecha, token, accion]) or accion not in _ACCIONES:
        return _mensaje("Petición no válida", "Faltan parámetros o la acción no es válida.", 422)

    solicitud = _solicitud_valida(animal_id, fecha, token)
    if solicitud is None:
        return _mensaje("No se pudo procesar", "Este enlace no es válido, ya se usó o ha caducado.", 410)

    try:
        aplicar_decision(solicitud, accion)
    except SolicitudYaProcesadaError:
        return _mensaje("Solicitud ya resuelta", "Esta solicitud ya fue procesada (quizá desde el panel).", 410)

    return _mensaje(
        "Listo",
        f"Solicitud {'aceptada' if accion == 'aceptar' else 'rechazada'} correctamente.",
        200,
    )


def handler(event, context):
    metodo, recurso = event["httpMethod"], event["resource"]
    try:
        if (metodo, recurso) == ("GET", "/decision"):
            return _mostrar_confirmacion(event)
        if (metodo, recurso) == ("POST", "/decision"):
            return _confirmar_decision(event)
        return _mensaje("No encontrado", "Ruta no encontrada.", 404)
    except Exception:
        logger.exception("Error no controlado en /decision")
        return _mensaje("Error interno", "Ha ocurrido un error inesperado.", 500)
