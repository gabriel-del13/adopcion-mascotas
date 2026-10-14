"""Perfil e historial del cliente, y solicitudes creadas
con sesión iniciada. Cognito nativo + grupo CLIENTE.
El 'sub' sale del token, nunca de la URL ni del cuerpo: un cliente solo
puede leer y escribir su propio ítem. Rol IAM: lectura/escritura en
solicitudes, lectura de catalogo, AdminDeleteUser sobre el User Pool.
"""
from datetime import datetime, timedelta

import boto3
from pydantic import BaseModel, Field

from app.core import config
from app.core import repositorio_catalogo as repo_catalogo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.auth import requiere_cliente
from app.core.respuestas import ApiError, cuerpo_texto, envoltura, json_response
from app.core.tokens import generar_token
from app.models.solicitud import Solicitud
from app.services.notificador import obtener_notificador

cognito = boto3.client("cognito-idp", region_name=config.REGION)

TOKEN_DECISION_VALIDEZ = timedelta(days=7)


class PerfilEntrada(BaseModel):
    nombre: str = Field(min_length=1)
    telefono: str = Field(min_length=1)
    descripcionSituacion: str | None = None


class SolicitudClienteEntrada(BaseModel):
    animalId: str = Field(min_length=1)
    mensaje: str = Field(min_length=1)


def _obtener_perfil(event: dict) -> dict:
    sub = requiere_cliente(event)
    cliente = repo_solicitudes.obtener_cliente(sub)
    if cliente is None:
        raise ApiError(404, "Perfil no encontrado")
    return json_response(200, cliente)


def _actualizar_perfil(event: dict) -> dict:
    sub = requiere_cliente(event)
    entrada = PerfilEntrada.model_validate_json(cuerpo_texto(event) or "{}")
    actual = repo_solicitudes.obtener_cliente(sub)
    if actual is None:
        raise ApiError(404, "Perfil no encontrado")

    actualizado = actual.model_copy(
        update={
            "nombre": entrada.nombre,
            "telefono": entrada.telefono,
            "descripcionSituacion": entrada.descripcionSituacion,
        }
    )
    repo_solicitudes.actualizar_perfil_cliente(actualizado)
    return json_response(200, actualizado)


def _historial_solicitudes(event: dict) -> dict:
    sub = requiere_cliente(event)
    solicitudes = repo_solicitudes.listar_solicitudes_por_cliente(sub)
    return json_response(200, [s.model_dump(mode="json", exclude={"tokenHash", "tokenExpira"}) for s in solicitudes])


def _crear_solicitud_con_sesion(event: dict) -> dict:
    sub = requiere_cliente(event)
    entrada = SolicitudClienteEntrada.model_validate_json(cuerpo_texto(event) or "{}")

    perfil = repo_solicitudes.obtener_cliente(sub)
    if perfil is None:
        raise ApiError(404, "Perfil no encontrado")

    animal = repo_catalogo.obtener_animal(entrada.animalId)
    if animal is None:
        raise ApiError(404, "Animal no encontrado")

    guarderia = repo_catalogo.obtener_guarderia(animal.guarderiaId)
    if guarderia is None:
        raise ApiError(404, "Guardería no encontrada")

    token, token_hash = generar_token()
    solicitud = Solicitud(
        animalId=animal.id,
        guarderiaId=animal.guarderiaId,
        clienteId=sub,
        nombre=perfil.nombre,
        email=perfil.email,
        telefono=perfil.telefono,
        mensaje=entrada.mensaje,
        descripcionSituacion=perfil.descripcionSituacion,
        tokenHash=token_hash,
        tokenExpira=datetime.utcnow() + TOKEN_DECISION_VALIDEZ,
    )
    repo_solicitudes.crear_solicitud(solicitud)
    obtener_notificador().notificar_nueva_solicitud(solicitud, animal, guarderia, token)

    return json_response(201, solicitud.model_dump(mode="json", exclude={"tokenHash", "tokenExpira"}))


def _borrar_cuenta(event: dict) -> dict:
    """Primero las solicitudes, luego el perfil, y luego Cognito """
    sub = requiere_cliente(event)
    repo_solicitudes.eliminar_solicitudes_de_cliente(sub)
    repo_solicitudes.eliminar_cliente(sub)
    cognito.admin_delete_user(UserPoolId=config.USER_POOL_ID, Username=sub)
    return json_response(204)


@envoltura
def handler(event, context):
    metodo, recurso = event["httpMethod"], event["resource"]
    if (metodo, recurso) == ("GET", "/cliente/perfil"):
        return _obtener_perfil(event)
    if (metodo, recurso) == ("PUT", "/cliente/perfil"):
        return _actualizar_perfil(event)
    if (metodo, recurso) == ("GET", "/cliente/solicitudes"):
        return _historial_solicitudes(event)
    if (metodo, recurso) == ("POST", "/cliente/solicitudes"):
        return _crear_solicitud_con_sesion(event)
    if (metodo, recurso) == ("DELETE", "/cliente"):
        return _borrar_cuenta(event)
    raise ApiError(404, "Ruta no encontrada")