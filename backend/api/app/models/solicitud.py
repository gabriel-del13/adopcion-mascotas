from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class EstadoSolicitud(str, Enum):
    pendiente = "pendiente"
    aceptada = "aceptada"
    rechazada = "rechazada"


class Solicitud(BaseModel):
    animalId: str = Field(min_length=1)
    # Se copia del animal al crear la solicitud
    guarderiaId: str = Field(min_length=1)
    # None enlas solicitudes anónimas
    clienteId: str | None = None
    # Datos de contacto en el momento de solicitar, no del perfil delcliente
    nombre: str = Field(min_length=1)
    email: EmailStr
    telefono: str = Field(min_length=1)
    mensaje: str = Field(min_length=1)
    # Copiada del perfil del cliente si tiene cuenta y la rellenó
    descripcionSituacion: str | None = None
    estado: EstadoSolicitud = EstadoSolicitud.pendiente
    fecha: datetime = Field(default_factory=datetime.utcnow)
