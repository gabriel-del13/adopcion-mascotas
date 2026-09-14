"""Alta de animales por parte de una guardería.

Auth simulada por cabecera HTTP: quien llama debe ser la propia guardería
del {guarderia_id} de la URL, y esa guardería debe estar aprobada.
"""
from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core import repositorio_catalogo as repo
from app.core.auth_simulado import obtener_sub_autenticado
from app.models.animal import Animal, EdadAnimal, TipoAnimal
from app.models.guarderia import EstadoGuarderia

router = APIRouter(tags=["guardería"])


class AnimalEntrada(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: TipoAnimal
    edad: EdadAnimal
    descripcion: str = Field(min_length=1)
    # MVP: URLs de ejemplo. En producción son presignadas hacia S3
    fotos: list[str] = Field(default_factory=list, max_length=5)


@router.post("/guarderias/{guarderia_id}/animales", response_model=Animal, status_code=201)
def crear_animal(
    guarderia_id: str,
    entrada: AnimalEntrada,
    sub: str = Depends(obtener_sub_autenticado),
) -> Animal:
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede publicar animales para otra guardería")

    guarderia = repo.obtener_guarderia(guarderia_id)
    if guarderia is None:
        raise HTTPException(status_code=404, detail="Guardería no encontrada")
    if guarderia.estado != EstadoGuarderia.aprobada:
        raise HTTPException(status_code=403, detail="La guardería no está aprobada")

    animal = Animal(
        id=str(uuid4()),
        guarderiaId=guarderia_id,
        nombre=entrada.nombre,
        tipo=entrada.tipo,
        edad=entrada.edad,
        ciudad=entrada.ciudad,
        provincia=entrada.provincia,
        descripcion=entrada.descripcion,
        fotos=entrada.fotos,
        fechaPublicacion=date.today(),
    )
    repo.crear_animal(animal)

    return animal
