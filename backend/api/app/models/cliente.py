from datetime import date

from pydantic import BaseModel, EmailStr, Field


class Cliente(BaseModel):
    sub: str = Field(min_length=1)
    nombre: str = Field(min_length=1)
    email: EmailStr
    # Vacío al registrarse: el Post Confirmation Trigger crea el perfil vacío
    # Se completa luego esde el perfil.
    telefono: str = ""
    fechaRegistro: date
    # Vivienda, otros animales, experiencia previa, disponibilidad. Viaja en el correo a la protectora cuando el cliente solicita con cuenta (Opcional)
    descripcionSituacion: str | None = None
