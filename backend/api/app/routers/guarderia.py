"""Alta de animales por parte de una guardería.

JWT + grupo GUARDERIA: quien llama debe ser la propia guardería del
{guarderia_id} de la URL, y esa guardería debe estar aprobada.
"""
from datetime import date
from uuid import uuid4

import boto3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core import config
from app.core import repositorio_catalogo as repo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.core.auth import requiere_guarderia
from app.core.repositorio_solicitudes import SolicitudYaProcesadaError
from app.models.animal import Animal, EdadAnimal, EstadoAnimal, TipoAnimal
from app.models.guarderia import EstadoGuarderia, Guarderia
from app.models.solicitud import Solicitud
from app.services.decisiones import aplicar_decision

router = APIRouter(tags=["guardería"])

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
    # Las fotos no se mandan aquí: se suben aparte con
    # POST /guarderias/{id}/animales/{id}/fotos, ver más abajo.


class AnimalActualizacion(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: TipoAnimal
    edad: EdadAnimal
    estado: EstadoAnimal
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    # fotos no se edita por aquí: la gestiona la Lambda de thumbnails (altas)
    # y el borrado de animal (bajas). Editar el resto de campos no las toca.


class FotoEntrada(BaseModel):
    contentType: str = Field(min_length=1)


class PresignedPost(BaseModel):
    fotoId: str
    url: str
    fields: dict[str, str]


class PerfilGuarderiaEntrada(BaseModel):
    nombre: str = Field(min_length=1)
    telefono: str = Field(min_length=1)
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)


@router.post("/guarderias/{guarderia_id}/animales", response_model=Animal, status_code=201)
def crear_animal(
    guarderia_id: str,
    entrada: AnimalEntrada,
    sub: str = Depends(requiere_guarderia),
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
        fechaPublicacion=date.today(),
    )
    repo.crear_animal(animal)

    return animal


@router.put("/guarderia/perfil", response_model=Guarderia)
def actualizar_perfil(entrada: PerfilGuarderiaEntrada, sub: str = Depends(requiere_guarderia)) -> Guarderia:
    guarderia = repo.obtener_guarderia(sub)
    if guarderia is None:
        raise HTTPException(status_code=404, detail="Guardería no encontrada")

    repo.actualizar_perfil_guarderia(
        sub,
        nombre=entrada.nombre,
        telefono=entrada.telefono,
        ciudad=entrada.ciudad,
        provincia=entrada.provincia,
        descripcion=entrada.descripcion,
    )
    return repo.obtener_guarderia(sub)


def _obtener_animal_propio(guarderia_id: str, animal_id: str) -> Animal:
    animal = repo.obtener_animal_de_guarderia(guarderia_id, animal_id)
    if animal is None:
        raise HTTPException(status_code=404, detail="Animal no encontrado")
    return animal


@router.put("/guarderias/{guarderia_id}/animales/{animal_id}", response_model=Animal)
def editar_animal(
    guarderia_id: str,
    animal_id: str,
    entrada: AnimalActualizacion,
    sub: str = Depends(requiere_guarderia),
) -> Animal:
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede editar animales de otra guardería")

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
    return actualizado


@router.post("/guarderias/{guarderia_id}/animales/{animal_id}/fotos", response_model=PresignedPost)
def subir_foto(
    guarderia_id: str,
    animal_id: str,
    entrada: FotoEntrada,
    sub: str = Depends(requiere_guarderia),
) -> PresignedPost:
    """Devuelve una URL presignada de POST (no PUT: PUT no admite límite de
    tamaño) para que el navegador suba la foto directo a S3, sin pasar por la
    API. La clave del objeto la decide el servidor, nunca quien llama. El
    Content-Type declarado aquí se puede mentir; quien lo verifica de verdad
    es la Lambda de thumbnails al abrir el fichero con Pillow.
    """
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede publicar fotos de otra guardería")

    animal = _obtener_animal_propio(guarderia_id, animal_id)
    # Límite de mejor esfuerzo: varias peticiones simultáneas podrían colarse
    # por encima de 5 antes de que la primera termine de procesarse (fotos
    # solo crece cuando la Lambda de thumbnails confirma cada una). Caso poco
    # frecuente, mismo criterio que la falta de transacción entre tablas.
    if len(animal.fotos) >= MAX_FOTOS_POR_ANIMAL:
        raise HTTPException(status_code=409, detail=f"El animal ya tiene el máximo de {MAX_FOTOS_POR_ANIMAL} fotos")
    if entrada.contentType not in TIPOS_CONTENIDO_PERMITIDOS:
        raise HTTPException(status_code=422, detail="Tipo de imagen no admitido")

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
    return PresignedPost(fotoId=foto_id, url=presignada["url"], fields=presignada["fields"])


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


@router.delete("/guarderias/{guarderia_id}/animales/{animal_id}", status_code=204)
def eliminar_animal(guarderia_id: str, animal_id: str, sub: str = Depends(requiere_guarderia)) -> None:
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede eliminar animales de otra guardería")
    animal = _obtener_animal_propio(guarderia_id, animal_id)
    _borrar_fotos_de_animal(animal)
    repo.eliminar_animal(guarderia_id, animal_id)


@router.get(
    "/guarderias/{guarderia_id}/solicitudes",
    response_model=list[Solicitud],
    response_model_exclude={"tokenHash", "tokenExpira"},
)
def listar_solicitudes_recibidas(guarderia_id: str, sub: str = Depends(requiere_guarderia)) -> list[Solicitud]:
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede ver las solicitudes de otra guardería")
    return repo_solicitudes.listar_solicitudes_por_guarderia(guarderia_id)


def _obtener_solicitud_propia(guarderia_id: str, animal_id: str, fecha: str) -> Solicitud:
    solicitud = repo_solicitudes.obtener_solicitud(animal_id, fecha)
    if solicitud is None or solicitud.guarderiaId != guarderia_id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return solicitud


@router.post("/guarderias/{guarderia_id}/solicitudes/{animal_id}/aceptar", status_code=204)
def aceptar_solicitud(
    guarderia_id: str,
    animal_id: str,
    fecha: str,
    sub: str = Depends(requiere_guarderia),
) -> None:
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede gestionar solicitudes de otra guardería")
    solicitud = _obtener_solicitud_propia(guarderia_id, animal_id, fecha)
    try:
        aplicar_decision(solicitud, "aceptar")
    except SolicitudYaProcesadaError as error:
        raise HTTPException(status_code=409, detail="La solicitud ya fue procesada") from error


@router.post("/guarderias/{guarderia_id}/solicitudes/{animal_id}/rechazar", status_code=204)
def rechazar_solicitud(
    guarderia_id: str,
    animal_id: str,
    fecha: str,
    sub: str = Depends(requiere_guarderia),
) -> None:
    if sub != guarderia_id:
        raise HTTPException(status_code=403, detail="No puede gestionar solicitudes de otra guardería")
    solicitud = _obtener_solicitud_propia(guarderia_id, animal_id, fecha)
    try:
        aplicar_decision(solicitud, "rechazar")
    except SolicitudYaProcesadaError as error:
        raise HTTPException(status_code=409, detail="La solicitud ya fue procesada") from error
