"""Acceso a la tabla `solicitudes`: clientes y solicitudes de adopción.

La PK de una solicitud es ANIMAL#<animalId>, la SK es SOLICITUD#<timestamp>.
El GSI1 (por cliente) es disperso: solo se rellena cuando hay clienteId, así
que las solicitudes anónimas no aparecen en el historial de nadie (Como debe ser).

El cliente vive en esta misma tabla (PK=CLIENTE#<sub>, SK=METADATA), no en
`catalogo`: es dato personal, igual que las solicitudes.
"""
from datetime import timedelta

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.core import dynamo
from app.models.cliente import Cliente
from app.models.solicitud import EstadoSolicitud, Solicitud

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


def listar_solicitudes_por_cliente(sub: str) -> list[Solicitud]:
    respuesta = dynamo.tabla_solicitudes.query(
        IndexName="GSI-Solicitudes-Por-Cliente",
        KeyConditionExpression=Key("GSI1PK").eq(f"CLIENTE#{sub}"),
        ScanIndexForward=False,
    )
    return [Solicitud.model_validate(item) for item in respuesta["Items"]]


def _cliente_a_item(cliente: Cliente) -> dict:
    item = cliente.model_dump(mode="json", exclude_none=True)
    item["PK"] = f"CLIENTE#{cliente.sub}"
    item["SK"] = "METADATA"
    return item


def crear_cliente(cliente: Cliente) -> None:
    dynamo.tabla_solicitudes.put_item(Item=_cliente_a_item(cliente))


def obtener_cliente(sub: str) -> Cliente | None:
    respuesta = dynamo.tabla_solicitudes.get_item(Key={"PK": f"CLIENTE#{sub}", "SK": "METADATA"})
    item = respuesta.get("Item")
    return Cliente.model_validate(item) if item else None


def actualizar_perfil_cliente(cliente: Cliente) -> None:
    dynamo.tabla_solicitudes.put_item(Item=_cliente_a_item(cliente))


def eliminar_cliente(sub: str) -> None:
    dynamo.tabla_solicitudes.delete_item(Key={"PK": f"CLIENTE#{sub}", "SK": "METADATA"})


def listar_solicitudes_por_guarderia(guarderia_id: str) -> list[Solicitud]:
    respuesta = dynamo.tabla_solicitudes.query(
        IndexName="GSI-Solicitudes-Por-Guarderia",
        KeyConditionExpression=Key("GSI2PK").eq(f"GUARDERIA#{guarderia_id}"),
        ScanIndexForward=False,
    )
    return [Solicitud.model_validate(item) for item in respuesta["Items"]]


def eliminar_solicitudes_de_cliente(sub: str) -> None:
    for solicitud in listar_solicitudes_por_cliente(sub):
        dynamo.tabla_solicitudes.delete_item(
            Key={"PK": f"ANIMAL#{solicitud.animalId}", "SK": f"SOLICITUD#{solicitud.fecha.isoformat()}"}
        )


class SolicitudYaProcesadaError(Exception):
    """"""


def obtener_solicitud(animal_id: str, fecha_iso: str) -> Solicitud | None:
    respuesta = dynamo.tabla_solicitudes.get_item(Key={"PK": f"ANIMAL#{animal_id}", "SK": f"SOLICITUD#{fecha_iso}"})
    item = respuesta.get("Item")
    return Solicitud.model_validate(item) if item else None


def aceptar_solicitud(animal_id: str, fecha_iso: str) -> None:
    try:
        dynamo.tabla_solicitudes.update_item(
            Key={"PK": f"ANIMAL#{animal_id}", "SK": f"SOLICITUD#{fecha_iso}"},
            UpdateExpression="SET estado = :aceptada",
            ConditionExpression="estado = :pendiente",
            ExpressionAttributeValues={":aceptada": EstadoSolicitud.aceptada.value, ":pendiente": EstadoSolicitud.pendiente.value},
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise SolicitudYaProcesadaError from error
        raise


def rechazar_solicitud_anonima(animal_id: str, fecha_iso: str) -> None:
    try:
        dynamo.tabla_solicitudes.delete_item(
            Key={"PK": f"ANIMAL#{animal_id}", "SK": f"SOLICITUD#{fecha_iso}"},
            ConditionExpression="estado = :pendiente",
            ExpressionAttributeValues={":pendiente": EstadoSolicitud.pendiente.value},
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise SolicitudYaProcesadaError from error
        raise


def redactar_solicitud_cliente(animal_id: str, fecha_iso: str) -> None:
    try:
        dynamo.tabla_solicitudes.update_item(
            Key={"PK": f"ANIMAL#{animal_id}", "SK": f"SOLICITUD#{fecha_iso}"},
            UpdateExpression="SET estado = :rechazada REMOVE nombre, email, telefono, mensaje, descripcionSituacion",
            ConditionExpression="estado = :pendiente",
            ExpressionAttributeValues={":rechazada": EstadoSolicitud.rechazada.value, ":pendiente": EstadoSolicitud.pendiente.value},
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise SolicitudYaProcesadaError from error
        raise