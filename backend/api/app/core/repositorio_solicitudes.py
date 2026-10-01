"""Acceso a la tabla `solicitudes`: solicitudes de adopción.

La PK de una solicitud es ANIMAL#<animalId>, la SK es SOLICITUD#<timestamp>.
El GSI1 (por cliente) es disperso: solo se rellena cuando hay clienteId, así
que las solicitudes anónimas no aparecen en el historial de nadie (Como debe ser).
"""
from datetime import timedelta

from app.core import dynamo
from app.models.solicitud import Solicitud

TTL_SOLICITUDES = timedelta(days=365)  # 12 meses


def _solicitud_a_item(solicitud: Solicitud) -> dict:
    marca_temporal = solicitud.fecha.isoformat()
    item = solicitud.model_dump(mode="json", exclude_none=True)
    item["PK"] = f"ANIMAL#{solicitud.animalId}"
    item["SK"] = f"SOLICITUD#{marca_temporal}"
    item["ttl"] = int((solicitud.fecha + TTL_SOLICITUDES).timestamp())
    item["GSI2PK"] = f"GUARDERIA#{solicitud.guarderiaId}"
    item["GSI2SK"] = f"SOLICITUD#{marca_temporal}"

    if solicitud.clienteId:
        item["GSI1PK"] = f"CLIENTE#{solicitud.clienteId}"
        item["GSI1SK"] = f"SOLICITUD#{marca_temporal}"

    return item


def crear_solicitud(solicitud: Solicitud) -> None:
    dynamo.tabla_solicitudes.put_item(Item=_solicitud_a_item(solicitud))