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
    # Datos de contacto en el momento de solicitar, no del perfil del cliente.
    # Opcionales porque al rechazar una solicitud con clienteId se borran
    # (se conserva clienteId/estado/fecha para el historial, ver
    # repositorio_solicitudes.redactar_solicitud_cliente).
    nombre: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, min_length=1)
    mensaje: str | None = Field(default=None, min_length=1)
    # Copiada del perfil del cliente si tiene cuenta y la rellenó
    descripcionSituacion: str | None = None
    estado: EstadoSolicitud = EstadoSolicitud.pendiente
    fecha: datetime = Field(default_factory=datetime.utcnow)
    # Solo el hash (SHA-256) del token de decisión por correo, nunca el token
    # en claro. None en las que no llevan enlace de decisión, o tras resolverse.
    tokenHash: str | None = None
    tokenExpira: datetime | None = None
