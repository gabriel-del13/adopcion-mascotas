"""Piezas comunes a las 6 Lambdas de la API: traducir errores de negocio a
respuestas HTTP de API Gateway y serializar los modelos Pydantic a JSON.
"""
import base64
import json
import logging

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# Fase pendiente: origen abierto para poder probar contra la API real desde
# cualquier dominio (CloudFront/S3 o incluso file:// en local).
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization,content-type",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


class ApiError(Exception):

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


def _serializar(cuerpo):
    if isinstance(cuerpo, BaseModel):
        return cuerpo.model_dump(mode="json")
    if isinstance(cuerpo, list):
        return [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in cuerpo]
    return cuerpo


def json_response(status_code: int, cuerpo=None) -> dict:
    return {
        "statusCode": status_code,
        "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(_serializar(cuerpo), ensure_ascii=False) if cuerpo is not None else "",
    }


def cuerpo_texto(event: dict) -> str:
    """Decodifica el body del evento de API Gateway, incluyendo el caso de `isBase64Encoded`."""
    cuerpo = event.get("body") or ""
    if event.get("isBase64Encoded"):
        cuerpo = base64.b64decode(cuerpo).decode()
    return cuerpo


def parsear_enum(valor: str | None, enum_cls, default=None):
    """404 si falta y no hay default, 422 si el valor no es un miembro válido."""
    if valor is None:
        return default
    try:
        return enum_cls(valor)
    except ValueError:
        raise ApiError(422, f"Valor no válido para {enum_cls.__name__}: {valor}")


def envoltura(despachar):
    """Decora la función de entrada de cada Lambda: traduce `ApiError` y los
    errores de validación de Pydantic a respuesta HTTP."""

    def handler(event, context):
        try:
            return despachar(event, context)
        except ApiError as error:
            return json_response(error.status_code, {"detail": error.detail})
        except ValidationError as error:
            return json_response(422, {"detail": error.errors()})
        except Exception:
            logger.exception("Error no controlado")
            return json_response(500, {"detail": "Error interno"})

    return handler
