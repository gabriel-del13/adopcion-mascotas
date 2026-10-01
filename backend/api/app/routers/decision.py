""""""
import logging
from datetime import datetime
from html import escape
from typing import Literal

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.repositorio_solicitudes import SolicitudYaProcesadaError
from app.core.tokens import verificar_token
from app.models.solicitud import EstadoSolicitud, Solicitud
from app.services.decisiones import aplicar_decision

router = APIRouter(tags=["decisión"])

logger = logging.getLogger(__name__)

Accion = Literal["aceptar", "rechazar"]

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


def _mensaje(titulo: str, texto: str, estado_http: int) -> HTMLResponse:
    return HTMLResponse(_pagina(titulo, f"<p>{texto}</p>"), status_code=estado_http)


def _solicitud_valida(animal_id: str, fecha: str, token: str) -> Solicitud | None:
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


@router.get("/decision", response_class=HTMLResponse)
def mostrar_confirmacion(animalId: str, fecha: str, token: str, accion: Accion) -> HTMLResponse:
    solicitud = repo_solicitudes.obtener_solicitud(animalId, fecha)
    if solicitud is None:
        return _mensaje("Solicitud no encontrada", "Esta solicitud no existe o ya fue eliminada.", 404)
    if solicitud.estado != EstadoSolicitud.pendiente:
        return _mensaje("Solicitud ya resuelta", "Esta solicitud ya fue aceptada o rechazada anteriormente.", 410)
    if _solicitud_valida(animalId, fecha, token) is None:
        return _mensaje("Enlace no válido", "Este enlace no es válido o ha caducado.", 403)

    cuerpo = f"""
    <dl>
      <dt>Adoptante</dt><dd>{escape(solicitud.nombre or "")}</dd>
      <dt>Mensaje</dt><dd>{escape(solicitud.mensaje or "")}</dd>
    </dl>
    <p>¿Confirmas que quieres <strong>{_ETIQUETA_ACCION[accion].lower()}</strong> esta solicitud?</p>
    <form method="post" action="/decision">
      <input type="hidden" name="animalId" value="{escape(animalId)}">
      <input type="hidden" name="fecha" value="{escape(fecha)}">
      <input type="hidden" name="token" value="{escape(token)}">
      <input type="hidden" name="accion" value="{escape(accion)}">
      <button type="submit">{_ETIQUETA_ACCION[accion]} solicitud</button>
    </form>
    """
    return HTMLResponse(_pagina("Confirmar decisión", cuerpo))


@router.post("/decision", response_class=HTMLResponse)
def confirmar_decision(
    animalId: str = Form(...),
    fecha: str = Form(...),
    token: str = Form(...),
    accion: Accion = Form(...),
) -> HTMLResponse:
    solicitud = _solicitud_valida(animalId, fecha, token)
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
