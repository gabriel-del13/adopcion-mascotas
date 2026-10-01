"""Catálogo público: listado y ficha de animales, listado de guarderías.

Sin autenticación: es la zona que cualquiera puede ver sin registrarse.
"""
from fastapi import APIRouter, HTTPException

from app.core import repositorio_catalogo as repo
from app.models.animal import Animal, EdadAnimal, EstadoAnimal, TipoAnimal
from app.models.guarderia import Guarderia

router = APIRouter(tags=["público"])


@router.get("/animales", response_model=list[Animal])
def listar_animales(
    estado: EstadoAnimal = EstadoAnimal.disponible,
    tipo: TipoAnimal | None = None,
    edad: EdadAnimal | None = None,
) -> list[Animal]:
    return repo.listar_animales(estado=estado, tipo=tipo, edad=edad)


@router.get("/animales/{animal_id}", response_model=Animal)
def obtener_animal(animal_id: str) -> Animal:
    animal = repo.obtener_animal(animal_id)
    if animal is None:
        raise HTTPException(status_code=404, detail="Animal no encontrado")
    return animal


@router.get("/guarderias", response_model=list[Guarderia])
def listar_guarderias() -> list[Guarderia]:
    return repo.listar_guarderias_aprobadas()
