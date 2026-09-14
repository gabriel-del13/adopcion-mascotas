"""POST anónimo del formulario de interés por un animal.

Sin autenticación: este el camino de quien pregunta sin crearse una cuenta.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core import repositorio_catalogo as repo_catalogo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.models.solicitud import Solicitud
from app.services.notificador import obtener_notificador

router = APIRouter(tags=["solicitudes"])


class SolicitudEntrada(BaseModel):
    animalId: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    email: EmailStr
    telefono: str = Field(min_length=1)
    mensaje: str = Field(min_length=1)


@router.post("/solicitudes", response_model=Solicitud, status_code=201)
def crear_solicitud(entrada: SolicitudEntrada) -> Solicitud:
    animal = repo_catalogo.obtener_animal(entrada.animalId)
    if animal is None:
        raise HTTPException(status_code=404, detail="Animal no encontrado")

    guarderia = repo_catalogo.obtener_guarderia(animal.guarderiaId)
    if guarderia is None:
        raise HTTPException(status_code=404, detail="Guardería no encontrada")

    solicitud = Solicitud(
        animalId=animal.id,
        guarderiaId=animal.guarderiaId,
        nombre=entrada.nombre,
        email=entrada.email,
        telefono=entrada.telefono,
        mensaje=entrada.mensaje,
    )
    repo_solicitudes.crear_solicitud(solicitud)
    obtener_notificador().notificar_nueva_solicitud(solicitud, animal, guarderia)

    return solicitud
