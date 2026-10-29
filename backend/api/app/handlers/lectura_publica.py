"""Catálogo público (listado y ficha de animales, listado
de guarderías aprobadas). 
cualquiera puede ver sin registrarse. 
Rol IAM: solo lectura sobre catalogo.
"""
from app.core import repositorio_catalogo as repo
from app.core.respuestas import ApiError, envoltura, json_response, parsear_enum
from app.models.animal import EdadAnimal, EstadoAnimal, TipoAnimal


def _listar_animales(event: dict) -> dict:
    query = event.get("queryStringParameters") or {}
    estado = parsear_enum(query.get("estado"), EstadoAnimal, EstadoAnimal.disponible)
    tipo = parsear_enum(query.get("tipo"), TipoAnimal)
    edad = parsear_enum(query.get("edad"), EdadAnimal)
    return json_response(200, repo.listar_animales(estado=estado, tipo=tipo, edad=edad))


def _obtener_animal(event: dict) -> dict:
    animal_id = event["pathParameters"]["animal_id"]
    animal = repo.obtener_animal(animal_id)
    if animal is None:
        raise ApiError(404, "Animal no encontrado")
    return json_response(200, animal)


def _listar_guarderias(event: dict) -> dict:
    return json_response(200, repo.listar_guarderias_aprobadas())


@envoltura
def handler(event, context):
    metodo, recurso = event["httpMethod"], event["resource"]
    if (metodo, recurso) == ("GET", "/animales"):
        return _listar_animales(event)
    if (metodo, recurso) == ("GET", "/animales/{animal_id}"):
        return _obtener_animal(event)
    if (metodo, recurso) == ("GET", "/guarderias"):
        return _listar_guarderias(event)
    raise ApiError(404, "Ruta no encontrada")
