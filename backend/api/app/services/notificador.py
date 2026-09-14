"""Aviso a la guardería cuando llega una solicitud de adopción.

#MVP: Interfaz con una implementación por ahora (`consola`). `ses` y `sns` se
añaden cuando haya recursos reales de SES/SNS contra los que probarlos;
mientras tanto seleccionar cualquier otro valor de NOTIFICADOR falla con
un error en vez de simular un envío que no se puede verificar.
"""
from abc import ABC, abstractmethod

from app.core import config
from app.models.animal import Animal
from app.models.guarderia import Guarderia
from app.models.solicitud import Solicitud


class Notificador(ABC):
    @abstractmethod
    def notificar_nueva_solicitud(self, solicitud: Solicitud, animal: Animal, guarderia: Guarderia) -> None: ...


class NotificadorConsola(Notificador):
    """Imprime el aviso por stdout. Notificador por defecto en el MVP."""

    def notificar_nueva_solicitud(self, solicitud: Solicitud, animal: Animal, guarderia: Guarderia) -> None:
        lineas = [
            "\n--- Nueva solicitud de adopción ---",
            f"Para: {guarderia.nombre} <{guarderia.email}>",
            f"Animal: {animal.nombre} ({animal.tipo.value}, {animal.edad.value})",
            f"Adoptante: {solicitud.nombre} <{solicitud.email}> - {solicitud.telefono}",
            f"Mensaje: {solicitud.mensaje}",
        ]
        if solicitud.descripcionSituacion:
            lineas.append(f"Situación del adoptante: {solicitud.descripcionSituacion}")
        # MVP: el correo real de producción incluye dos enlaces para aceptar orechazar sin entrar al panel. Esos endpoints todavía no existen.
        lineas.append("------------------------------------\n")
        print("\n".join(lineas))


def obtener_notificador() -> Notificador:
    if config.NOTIFICADOR == "consola":
        return NotificadorConsola()
    raise NotImplementedError(f"Notificador '{config.NOTIFICADOR}' no implementado todavía.")
