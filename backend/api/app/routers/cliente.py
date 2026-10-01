"""Perfil e historial del cliente, y solicitudes creadas con sesión iniciada.

JWT + grupo CLIENTE. El `sub` sale del token, nunca de la URL ni del cuerpo:
un cliente solo puede leer y escribir su propio ítem.
"""
from datetime import datetime, timedelta

import boto3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core import config
from app.core import repositorio_catalogo as repo_catalogo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.auth import requiere_cliente
from app.core.tokens import generar_token
from app.models.cliente import Cliente
from app.models.solicitud import Solicitud
from app.services.notificador import obtener_notificador

cognito = boto3.client("cognito-idp", region_name=config.REGION)

router = APIRouter(prefix="/cliente", tags=["cliente"])

TOKEN_DECISION_VALIDEZ = timedelta(days=7)


class PerfilEntrada(BaseModel):
    nombre: str = Field(min_length=1)
    telefono: str = Field(min_length=1)
    descripcionSituacion: str | None = None


class SolicitudClienteEntrada(BaseModel):
    animalId: str = Field(min_length=1)
    mensaje: str = Field(min_length=1)


@router.get("/perfil", response_model=Cliente)
def obtener_perfil(sub: str = Depends(requiere_cliente)) -> Cliente:
    cliente = repo_solicitudes.obtener_cliente(sub)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return cliente


@router.put("/perfil", response_model=Cliente)
def actualizar_perfil(entrada: PerfilEntrada, sub: str = Depends(requiere_cliente)) -> Cliente:
    actual = repo_solicitudes.obtener_cliente(sub)
    if actual is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    actualizado = actual.model_copy(
        update={
            "nombre": entrada.nombre,
            "telefono": entrada.telefono,
            "descripcionSituacion": entrada.descripcionSituacion,
        }
    )
    repo_solicitudes.actualizar_perfil_cliente(actualizado)
    return actualizado


@router.get(
    "/solicitudes",
    response_model=list[Solicitud],
    response_model_exclude={"tokenHash", "tokenExpira"},
)
def historial_solicitudes(sub: str = Depends(requiere_cliente)) -> list[Solicitud]:
    return repo_solicitudes.listar_solicitudes_por_cliente(sub)


@router.post(
    "/solicitudes",
    response_model=Solicitud,
    response_model_exclude={"tokenHash", "tokenExpira"},
    status_code=201,
)
def crear_solicitud_con_sesion(entrada: SolicitudClienteEntrada, sub: str = Depends(requiere_cliente)) -> Solicitud:
    perfil = repo_solicitudes.obtener_cliente(sub)
    if perfil is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    animal = repo_catalogo.obtener_animal(entrada.animalId)
    if animal is None:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    guarderia = repo_catalogo.obtener_guarderia(animal.guarderiaId)
    if guarderia is None:
        raise HTTPException(status_code=404, detail="Guardería no encontrada")

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

    return solicitud


@router.delete("", status_code=204)
def borrar_cuenta(sub: str = Depends(requiere_cliente)) -> None:
    """Derecho de supresión en autoservicio. Orden importante: primero las solicitudes, luego el perfil, y
    solo entonces Cognito — si se borrase el usuario de Cognito primero, un
    fallo a mitad dejaría datos huérfanos sin dueño identificable.
    """
    repo_solicitudes.eliminar_solicitudes_de_cliente(sub)
    repo_solicitudes.eliminar_cliente(sub)
    cognito.admin_delete_user(UserPoolId=config.USER_POOL_ID, Username=sub)
