"""Aviso a la guardería cuando llega una solicitud de adopción.

Dos implementaciones: `consola` (por defecto en local, imprime por stdout) y
`sqs` (encola un mensaje para que la Lambda consumidora de
infra/templates/notificaciones.yaml envíe el correo real por SES). `sns` queda
reservado para alertas operativas al administrador, no para este aviso.

El token de decisión viaja en claro solo hasta aquí: en DynamoDB
(`solicitud.tokenHash`) ya se guardó el hash, nunca el token
"""
import json
from abc import ABC, abstractmethod
from typing import Literal
from urllib.parse import urlencode

import boto3

from app.core import config
from app.models.animal import Animal
from app.models.guarderia import Guarderia
from app.models.solicitud import Solicitud


def _enlace_decision(solicitud: Solicitud, token: str, accion: Literal["aceptar", "rechazar"]) -> str:
    parametros = urlencode(
        {
            "animalId": solicitud.animalId,
            "fecha": solicitud.fecha.isoformat(),
            "token": token,
            "accion": accion,
        }
    )
    return f"{config.API_BASE_URL}/decision?{parametros}"


class Notificador(ABC):
    @abstractmethod
    def notificar_nueva_solicitud(self, solicitud: Solicitud, animal: Animal, guarderia: Guarderia, token: str) -> None: ...


class NotificadorConsola(Notificador):
    """Imprime el aviso por stdout. Notificador por defecto en el MVP."""

    def notificar_nueva_solicitud(self, solicitud: Solicitud, animal: Animal, guarderia: Guarderia, token: str) -> None:
        lineas = [
            "\n--- Nueva solicitud de adopción ---",
            f"Para: {guarderia.nombre} <{guarderia.email}>",
            f"Animal: {animal.nombre} ({animal.tipo.value}, {animal.edad.value})",
            f"Adoptante: {solicitud.nombre} <{solicitud.email}> - {solicitud.telefono}",
            f"Mensaje: {solicitud.mensaje}",
        ]
        if solicitud.descripcionSituacion:
            lineas.append(f"Situación del adoptante: {solicitud.descripcionSituacion}")
        lineas.append(f"Aceptar: {_enlace_decision(solicitud, token, 'aceptar')}")
        lineas.append(f"Rechazar: {_enlace_decision(solicitud, token, 'rechazar')}")
        lineas.append("------------------------------------\n")
        print("\n".join(lineas))


class NotificadorSqs(Notificador):
    """Encola el aviso; la Lambda consumidora arma el correo y lo envía por
    SES. El mensaje lleva ya todo lo necesario para componerlo: la
    consumidora no tiene ningún permiso sobre DynamoDB."""

    def __init__(self) -> None:
        self._cliente = boto3.client("sqs", region_name=config.REGION)

    def notificar_nueva_solicitud(self, solicitud: Solicitud, animal: Animal, guarderia: Guarderia, token: str) -> None:
        mensaje = {
            "tipo": "nueva_solicitud",
            "guarderiaEmail": guarderia.email,
            "guarderiaNombre": guarderia.nombre,
            "animalNombre": animal.nombre,
            "animalTipo": animal.tipo.value,
            "animalEdad": animal.edad.value,
            "adoptanteNombre": solicitud.nombre,
            "adoptanteEmail": solicitud.email,
            "adoptanteTelefono": solicitud.telefono,
            "mensaje": solicitud.mensaje,
            "descripcionSituacion": solicitud.descripcionSituacion,
            "esClienteConCuenta": solicitud.clienteId is not None,
            "enlaceAceptar": _enlace_decision(solicitud, token, "aceptar"),
            "enlaceRechazar": _enlace_decision(solicitud, token, "rechazar"),
        }
        self._cliente.send_message(QueueUrl=config.COLA_NOTIFICACIONES_URL, MessageBody=json.dumps(mensaje))


def obtener_notificador() -> Notificador:
    if config.NOTIFICADOR == "consola":
        return NotificadorConsola()
    if config.NOTIFICADOR == "sqs":
        return NotificadorSqs()
    raise NotImplementedError(f"Notificador '{config.NOTIFICADOR}' no implementado todavía.")
