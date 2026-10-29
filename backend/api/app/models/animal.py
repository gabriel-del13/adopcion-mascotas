from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class TipoAnimal(str, Enum):
    perro = "perro"
    gato = "gato"
    otro = "otro"


class EdadAnimal(str, Enum):
    cachorro = "cachorro"
    joven = "joven"
    adulto = "adulto"
    senior = "senior"


class EstadoAnimal(str, Enum):
    disponible = "disponible"
    no_disponible = "no_disponible"
    en_proceso = "en_proceso"
    adoptado = "adoptado"


class Animal(BaseModel):
    id: str = Field(min_length=1)
    guarderiaId: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    tipo: TipoAnimal
    edad: EdadAnimal
    estado: EstadoAnimal = EstadoAnimal.disponible
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    # Ids de foto (uuid4), no URLs: la sube el navegador a S3 con una
    # presignada de POST (POST /guarderias/{id}/animales/{id}/fotos) y la
    # Lambda de thumbnails los añade aquí tras generar las dos derivadas
    # (400px y 1200px, WebP, sin EXIF). Sin URL pública todavía porque no hay
    # CloudFront delante del bucket de derivadas (fase pendiente); se lee a
    # mano con `aws s3 cp` hasta entonces.
    fotos: list[str] = Field(default_factory=list, max_length=5)
    fechaPublicacion: date
    # Solo sube cuando se rechaza una solicitud anónima sobre este animal: es la única traza que queda de esa solicitud
    contadorRechazosAnonimos: int = 0
