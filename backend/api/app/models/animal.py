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
    # MVP: URLs de ejemplo. En producción son presignadas hacia S3
    fotos: list[str] = Field(default_factory=list, max_length=5)
    fechaPublicacion: date
