"""Recursos boto3 de las dos tablas de DynamoDB.

Tabla `catalogo`: datos publicables (guarderías, animales).
Tabla `solicitudes`: datos personales (clientes, solicitudes).
"""
import os

import boto3

from app.core import config

# Credenciales dummy: DynamoDB Local no las valida, pero boto3 exige que existan para construir el recurso.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "local")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "local")

_recurso = boto3.resource(
    "dynamodb",
    region_name=config.REGION,
    endpoint_url=config.DYNAMODB_ENDPOINT_URL,
)

tabla_catalogo = _recurso.Table(config.TABLA_CATALOGO)
tabla_solicitudes = _recurso.Table(config.TABLA_SOLICITUDES)