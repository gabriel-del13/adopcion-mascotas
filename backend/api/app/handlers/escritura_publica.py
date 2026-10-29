"""POST anónimo del formulario de interés por un animal.
Sin autenticación: este es el camino de quien pregunta sin crearse una
cuenta (la protección de esta ruta es WAF). Rol IAM: solo
PutItem en solicitudes, lectura de catalogo, SendMessage a la cola de
notificaciones.
"""
from datetime import datetime, timedelta

from pydantic import BaseModel, EmailStr, Field

from app.core import repositorio_catalogo as repo_catalogo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.respuestas import ApiError, cuerpo_texto, envoltura, json_response
from app.core.tokens import generar_token
from app.models.solicitud import Solicitud
from app.services.notificador import obtener_notificador

TOKEN_DECISION_VALIDEZ = timedelta(days=7)


class SolicitudEntrada(BaseModel):
    animalId: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    email: EmailStr
    telefono: str = Field(min_length=1)
    mensaje: str = Field(min_length=1)


def _crear_solicitud(event: dict) -> dict:
    entrada = SolicitudEntrada.model_validate_json(cuerpo_texto(event) or "{}")

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
        nombre=entrada.nombre,
        email=entrada.email,
        telefono=entrada.telefono,
        mensaje=entrada.mensaje,
        tokenHash=token_hash,
        tokenExpira=datetime.utcnow() + TOKEN_DECISION_VALIDEZ,
    )
    repo_solicitudes.crear_solicitud(solicitud)
    obtener_notificador().notificar_nueva_solicitud(solicitud, animal, guarderia, token)

    return json_response(201, solicitud.model_dump(mode="json", exclude={"tokenHash", "tokenExpira"}))


@envoltura
def handler(event, context):
    if (event["httpMethod"], event["resource"]) == ("POST", "/solicitudes"):
        return _crear_solicitud(event)
    raise ApiError(404, "Ruta no encontrada")
