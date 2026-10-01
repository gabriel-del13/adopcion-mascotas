from datetime import date

from pydantic import BaseModel, EmailStr, Field


class Cliente(BaseModel):
    sub: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    email: EmailStr
    telefono: str = Field(min_length=1)
    fechaRegistro: date
    # Vivienda, otros animales, experiencia previa, disponibilidad. Viaja en el correo a la protectora cuando el cliente solicita con cuenta (Opcional)
    descripcionSituacion: str | None = None
