"""Gestión de animales por la guardería (alta, edición, baja, fotos), 
perfil propio y solicitudes recibidas (listar/aceptar/rechazar). 
Cognito nativo + grupo GUARDERIA. 
Rol IAM: escritura en catalogo, lectura/escritura del GSI de solicitudes por guardería
S3 PutObject/DeleteObject en los buckets de fotos.
"""
from datetime import date
from uuid import uuid4

import boto3
from pydantic import BaseModel, Field

from app.core import config
from app.core import repositorio_catalogo as repo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.auth import requiere_guarderia
from app.core.repositorio_solicitudes import SolicitudYaProcesadaError
from app.core.respuestas import ApiError, cuerpo_texto, envoltura, json_response
from app.models.animal import Animal, EdadAnimal, EstadoAnimal, TipoAnimal
from app.models.guarderia import EstadoGuarderia, Guarderia
from app.services.decisiones import aplicar_decision

s3 = boto3.client("s3", region_name=config.REGION)

MAX_FOTOS_POR_ANIMAL = 5
TIPOS_CONTENIDO_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
TAMANO_MIN_FOTO = 10 * 1024
TAMANO_MAX_FOTO = 8 * 1024 * 1024


class AnimalEntrada(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: TipoAnimal
    edad: EdadAnimal
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)


class AnimalActualizacion(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: TipoAnimal
    edad: EdadAnimal
    estado: EstadoAnimal
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)


class FotoEntrada(BaseModel):
    contentType: str = Field(min_length=1)


class PerfilGuarderiaEntrada(BaseModel):
    nombre: str = Field(min_length=1)
    telefono: str = Field(min_length=1)
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)


def _obtener_animal_propio(guarderia_id: str, animal_id: str) -> Animal:
    animal = repo.obtener_animal_de_guarderia(guarderia_id, animal_id)
    if animal is None:
        raise ApiError(404, "Animal no encontrado")
    return animal


def _borrar_fotos_de_animal(animal: Animal) -> None:
    """Borra original + las dos derivadas de cada foto. Se llama antes de
    borrar el ítem del animal."""
    if not animal.fotos:
        return

    prefijo = f"animales/{animal.guarderiaId}/{animal.id}"
    claves_originales = [{"Key": f"{prefijo}/{foto_id}"} for foto_id in animal.fotos]
    claves_derivadas = [
        {"Key": f"{prefijo}/{foto_id}-{tamano}.webp"} for foto_id in animal.fotos for tamano in ("400", "1200")
    ]
    s3.delete_objects(Bucket=config.BUCKET_FOTOS_ORIGINALES, Delete={"Objects": claves_originales})
    s3.delete_objects(Bucket=config.BUCKET_FOTOS_DERIVADAS, Delete={"Objects": claves_derivadas})


def _crear_animal(event: dict) -> dict:
    guarderia_id = event["pathParameters"]["guarderia_id"]
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede publicar animales para otra guardería")

    entrada = AnimalEntrada.model_validate_json(cuerpo_texto(event) or "{}")

    guarderia = repo.obtener_guarderia(guarderia_id)
    if guarderia is None:
        raise ApiError(404, "Guardería no encontrada")
    if guarderia.estado != EstadoGuarderia.aprobada:
        raise ApiError(403, "La guardería no está aprobada")

    animal = Animal(
        id=str(uuid4()),
        guarderiaId=guarderia_id,
        nombre=entrada.nombre,
        tipo=entrada.tipo,
        edad=entrada.edad,
        ciudad=entrada.ciudad,
        provincia=entrada.provincia,
        descripcion=entrada.descripcion,
        fechaPublicacion=date.today(),
    )
    repo.crear_animal(animal)

    return json_response(201, animal)


def _actualizar_perfil(event: dict) -> dict:
    sub = requiere_guarderia(event)
    entrada = PerfilGuarderiaEntrada.model_validate_json(cuerpo_texto(event) or "{}")

    guarderia = repo.obtener_guarderia(sub)
    if guarderia is None:
        raise ApiError(404, "Guardería no encontrada")

    repo.actualizar_perfil_guarderia(
        sub,
        nombre=entrada.nombre,
        telefono=entrada.telefono,
        ciudad=entrada.ciudad,
        provincia=entrada.provincia,
        descripcion=entrada.descripcion,
    )
    return json_response(200, repo.obtener_guarderia(sub))


def _editar_animal(event: dict) -> dict:
    guarderia_id = event["pathParameters"]["guarderia_id"]
    animal_id = event["pathParameters"]["animal_id"]
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede editar animales de otra guardería")

    entrada = AnimalActualizacion.model_validate_json(cuerpo_texto(event) or "{}")
    actual = _obtener_animal_propio(guarderia_id, animal_id)
    actualizado = actual.model_copy(
        update={
            "nombre": entrada.nombre,
            "tipo": entrada.tipo,
            "edad": entrada.edad,
            "estado": entrada.estado,
            "ciudad": entrada.ciudad,
            "provincia": entrada.provincia,
            "descripcion": entrada.descripcion,
        }
    )
    repo.actualizar_animal(actualizado)
    return json_response(200, actualizado)


def _subir_foto(event: dict) -> dict:
    """Devuelve una URL presignada de POST (no PUT: PUT no admite límite de
    tamaño) para que el navegador suba la foto directo a S3, sin pasar por
    la API. La clave del objeto la decide el servidor. El
    Content-Type declarado aquí se puede mentir; quien lo verifica de verdad
    es la Lambda de thumbnails"""
    guarderia_id = event["pathParameters"]["guarderia_id"]
    animal_id = event["pathParameters"]["animal_id"]
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede publicar fotos de otra guardería")

    entrada = FotoEntrada.model_validate_json(cuerpo_texto(event) or "{}")
    animal = _obtener_animal_propio(guarderia_id, animal_id)
    if len(animal.fotos) >= MAX_FOTOS_POR_ANIMAL:
        raise ApiError(409, f"El animal ya tiene el máximo de {MAX_FOTOS_POR_ANIMAL} fotos")
    if entrada.contentType not in TIPOS_CONTENIDO_PERMITIDOS:
        raise ApiError(422, "Tipo de imagen no admitido")

    foto_id = str(uuid4())
    clave = f"animales/{guarderia_id}/{animal_id}/{foto_id}"
    presignada = s3.generate_presigned_post(
        Bucket=config.BUCKET_FOTOS_ORIGINALES,
        Key=clave,
        Fields={"Content-Type": entrada.contentType},
        Conditions=[
            {"Content-Type": entrada.contentType},
            ["content-length-range", TAMANO_MIN_FOTO, TAMANO_MAX_FOTO],
        ],
        ExpiresIn=300,
    )
    return json_response(200, {"fotoId": foto_id, "url": presignada["url"], "fields": presignada["fields"]})


def _eliminar_animal(event: dict) -> dict:
    guarderia_id = event["pathParameters"]["guarderia_id"]
    animal_id = event["pathParameters"]["animal_id"]
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede eliminar animales de otra guardería")
    animal = _obtener_animal_propio(guarderia_id, animal_id)
    _borrar_fotos_de_animal(animal)
    repo.eliminar_animal(guarderia_id, animal_id)
    return json_response(204)


def _listar_solicitudes_recibidas(event: dict) -> dict:
    guarderia_id = event["pathParameters"]["guarderia_id"]
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede ver las solicitudes de otra guardería")
    solicitudes = repo_solicitudes.listar_solicitudes_por_guarderia(guarderia_id)
    return json_response(200, [s.model_dump(mode="json", exclude={"tokenHash", "tokenExpira"}) for s in solicitudes])


def _obtener_solicitud_propia(guarderia_id: str, animal_id: str, fecha: str):
    solicitud = repo_solicitudes.obtener_solicitud(animal_id, fecha)
    if solicitud is None or solicitud.guarderiaId != guarderia_id:
        raise ApiError(404, "Solicitud no encontrada")
    return solicitud


def _aceptar_solicitud(event: dict) -> dict:
    guarderia_id = event["pathParameters"]["guarderia_id"]
    animal_id = event["pathParameters"]["animal_id"]
    fecha = (event.get("queryStringParameters") or {}).get("fecha")
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede gestionar solicitudes de otra guardería")
    solicitud = _obtener_solicitud_propia(guarderia_id, animal_id, fecha)
    try:
        aplicar_decision(solicitud, "aceptar")
    except SolicitudYaProcesadaError as error:
        raise ApiError(409, "La solicitud ya fue procesada") from error
    return json_response(204)


def _rechazar_solicitud(event: dict) -> dict:
    guarderia_id = event["pathParameters"]["guarderia_id"]
    animal_id = event["pathParameters"]["animal_id"]
    fecha = (event.get("queryStringParameters") or {}).get("fecha")
    sub = requiere_guarderia(event)
    if sub != guarderia_id:
        raise ApiError(403, "No puede gestionar solicitudes de otra guardería")
    solicitud = _obtener_solicitud_propia(guarderia_id, animal_id, fecha)
    try:
        aplicar_decision(solicitud, "rechazar")
    except SolicitudYaProcesadaError as error:
        raise ApiError(409, "La solicitud ya fue procesada") from error
    return json_response(204)


@envoltura
def handler(event, context):
    metodo, recurso = event["httpMethod"], event["resource"]
    if (metodo, recurso) == ("POST", "/guarderias/{guarderia_id}/animales"):
        return _crear_animal(event)
    if (metodo, recurso) == ("PUT", "/guarderia/perfil"):
        return _actualizar_perfil(event)
    if (metodo, recurso) == ("PUT", "/guarderias/{guarderia_id}/animales/{animal_id}"):
        return _editar_animal(event)
    if (metodo, recurso) == ("POST", "/guarderias/{guarderia_id}/animales/{animal_id}/fotos"):
        return _subir_foto(event)
    if (metodo, recurso) == ("DELETE", "/guarderias/{guarderia_id}/animales/{animal_id}"):
        return _eliminar_animal(event)
    if (metodo, recurso) == ("GET", "/guarderias/{guarderia_id}/solicitudes"):
        return _listar_solicitudes_recibidas(event)
    if (metodo, recurso) == ("POST", "/guarderias/{guarderia_id}/solicitudes/{animal_id}/aceptar"):
        return _aceptar_solicitud(event)
    if (metodo, recurso) == ("POST", "/guarderias/{guarderia_id}/solicitudes/{animal_id}/rechazar"):
        return _rechazar_solicitud(event)
    raise ApiError(404, "Ruta no encontrada")