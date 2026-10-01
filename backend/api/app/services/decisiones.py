"""Aplica la decisión (aceptar/rechazar) de una guardería sobre una solicitud.
"""
from typing import Literal

from app.core import repositorio_catalogo as repo_catalogo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.models.animal import EstadoAnimal
from app.models.solicitud import Solicitud

Accion = Literal["aceptar", "rechazar"]


def aplicar_decision(solicitud: Solicitud, accion: Accion) -> None:
    fecha_iso = solicitud.fecha.isoformat()

    if accion == "aceptar":
        repo_solicitudes.aceptar_solicitud(solicitud.animalId, fecha_iso)
        repo_catalogo.marcar_estado_animal(solicitud.guarderiaId, solicitud.animalId, EstadoAnimal.en_proceso)
        return

    if solicitud.clienteId is None:
        repo_solicitudes.rechazar_solicitud_anonima(solicitud.animalId, fecha_iso)
        repo_catalogo.incrementar_contador_rechazos(solicitud.guarderiaId, solicitud.animalId)
    else:
        repo_solicitudes.redactar_solicitud_cliente(solicitud.animalId, fecha_iso)
