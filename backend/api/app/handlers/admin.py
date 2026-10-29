"""Entrypoint Lambda: aprobación de guarderías por el administrador.
Cognito nativo + grupo ADMIN. El grupo ADMIN no es alcanzable por auto-registro, 
solo lo asigna `admin-add-user-to-group` con
credenciales administrativas. Rol IAM: lectura/escritura solo sobre
catalogo.
"""
from pydantic import BaseModel, Field

from app.core import repositorio_catalogo as repo
from app.core.auth import requiere_admin
from app.core.respuestas import ApiError, cuerpo_texto, envoltura, json_response


class RechazoEntrada(BaseModel):
    motivo: str = Field(min_length=1)


def _listar_pendientes(event: dict) -> dict:
    requiere_admin(event)
    return json_response(200, repo.listar_guarderias_pendientes())


def _aprobar_guarderia(event: dict) -> dict:
    requiere_admin(event)
    sub = event["pathParameters"]["sub"]
    if repo.obtener_guarderia(sub) is None:
        raise ApiError(404, "Guardería no encontrada")
    repo.aprobar_guarderia(sub)
    return json_response(204)


def _rechazar_guarderia(event: dict) -> dict:
    requiere_admin(event)
    sub = event["pathParameters"]["sub"]
    entrada = RechazoEntrada.model_validate_json(cuerpo_texto(event) or "{}")
    if repo.obtener_guarderia(sub) is None:
        raise ApiError(404, "Guardería no encontrada")
    repo.rechazar_guarderia(sub, entrada.motivo)
    # Fase pendiente: aquí va el aviso por correo a la guardería (SQS → SES)
    return json_response(204)


@envoltura
def handler(event, context):
    metodo, recurso = event["httpMethod"], event["resource"]
    if (metodo, recurso) == ("GET", "/admin/guarderias/pendientes"):
        return _listar_pendientes(event)
    if (metodo, recurso) == ("POST", "/admin/guarderias/{sub}/aprobar"):
        return _aprobar_guarderia(event)
    if (metodo, recurso) == ("POST", "/admin/guarderias/{sub}/rechazar"):
        return _rechazar_guarderia(event)
    raise ApiError(404, "Ruta no encontrada")
