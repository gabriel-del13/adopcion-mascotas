"""Aprobación de guarderías por el administrador.

JWT + grupo ADMIN. El grupo ADMIN no es alcanzable por auto-registro solo lo asigna
`admin-add-user-to-group` con credenciales administrativas.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core import repositorio_catalogo as repo
from app.core.auth import requiere_admin
from app.models.guarderia import EstadoGuarderia, Guarderia

router = APIRouter(prefix="/admin", tags=["admin"])


class RechazoEntrada(BaseModel):
    motivo: str = Field(min_length=1)


@router.get("/guarderias/pendientes", response_model=list[Guarderia])
def listar_pendientes(_: str = Depends(requiere_admin)) -> list[Guarderia]:
    return repo.listar_guarderias_pendientes()


@router.post("/guarderias/{sub}/aprobar", status_code=204)
def aprobar_guarderia(sub: str, _: str = Depends(requiere_admin)) -> None:
    guarderia = repo.obtener_guarderia(sub)
    if guarderia is None:
        raise HTTPException(status_code=404, detail="Guardería no encontrada")
    repo.aprobar_guarderia(sub)


@router.post("/guarderias/{sub}/rechazar", status_code=204)
def rechazar_guarderia(sub: str, entrada: RechazoEntrada, _: str = Depends(requiere_admin)) -> None:
    guarderia = repo.obtener_guarderia(sub)
    if guarderia is None:
        raise HTTPException(status_code=404, detail="Guardería no encontrada")
    repo.rechazar_guarderia(sub, entrada.motivo)
    # Fase pendiente: aquí va el aviso por correo a la guardería (SQS → SES),
    # cuando exista esa infraestructura. Por ahora la decisión queda en la
    # tabla y el admin la comunica fuera de banda.
