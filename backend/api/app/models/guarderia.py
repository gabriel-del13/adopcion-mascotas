from datetime import date
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class EstadoGuarderia(str, Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    rechazada = "rechazada"


class Guarderia(BaseModel):
    sub: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    email: EmailStr
    telefono: str = Field(min_length=1)
    ciudad: str = Field(min_length=1)
    provincia: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    estado: EstadoGuarderia = EstadoGuarderia.pendiente
    fechaRegistro: date
    # Solo tiene valor cuando estado es "rechazada", el administrador indica el motivo al rechazar una guardería.
    motivoRechazo: str | None = None
