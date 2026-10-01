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
    # Vacíos al registrarse: el Post Confirmation Trigger solo conoce el
    # email. Se rellenan luego desde el panel de la guardería.
    telefono: str = ""
    ciudad: str = ""
    provincia: str = ""
    descripcion: str = ""
    estado: EstadoGuarderia = EstadoGuarderia.pendiente
    fechaRegistro: date
    # Solo tiene valor cuando estado es "rechazada", el administrador indica el motivo al rechazar una guardería.
    motivoRechazo: str | None = None
