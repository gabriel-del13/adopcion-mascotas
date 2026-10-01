"""Aplica la decisión (aceptar/rechazar) de una guardería sobre una solicitud.

Un solo sitio para la bifurcación anónima/con-cliente, reutilizado tanto por
el panel de la guardería (`routers/guarderia.py`, con sesión) como por el
enlace de decisión por correo (`routers/decision.py`, con token de un solo
uso
"""
from typing import Literal

from app.core import repositorio_catalogo as repo_catalogo
from app.core import repositorio_solicitudes as repo_solicitudes
from app.models.animal import EstadoAnimal
from app.models.solicitud import Solicitud

Accion = Literal["aceptar", "rechazar"]


def aplicar_decision(solicitud: Solicitud, accion: Accion) -> None:
    """Puede lanzar `repositorio_solicitudes.SolicitudYaProcesadaError` si la
    solicitud ya no está en `pendiente` (aceptar o rechazar dos veces)."""
    fecha_iso = solicitud.fecha.isoformat()

    if accion == "aceptar":
        repo_solicitudes.aceptar_solicitud(solicitud.animalId, fecha_iso)
        # El animal sale del catálogo mientras se cierran los trámites; volver
        # a "disponible" o pasar a "adoptado" es un PUT aparte cuando termine.
        repo_catalogo.marcar_estado_animal(solicitud.guarderiaId, solicitud.animalId, EstadoAnimal.en_proceso)
        return

    if solicitud.clienteId is None:
        repo_solicitudes.rechazar_solicitud_anonima(solicitud.animalId, fecha_iso)
        repo_catalogo.incrementar_contador_rechazos(solicitud.guarderiaId, solicitud.animalId)
    else:
        repo_solicitudes.redactar_solicitud_cliente(solicitud.animalId, fecha_iso)
