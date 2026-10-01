"""Configuración de entorno para la capa de acceso a datos.

# MVP: en AWS estos valores deben salir de SSM Parameter Store, no de
variables de entorno del Lambda. Se deja así mientras el MVP corre solo
en local contra DynamoDB Local.
"""
import os

REGION = os.environ.get("AWS_REGION", "eu-west-1")
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLA_CATALOGO = os.environ.get("TABLA_CATALOGO", "adopcion-mascotas-local-catalogo")
TABLA_SOLICITUDES = os.environ.get("TABLA_SOLICITUDES", "adopcion-mascotas-local-solicitudes")
NOTIFICADOR = os.environ.get("NOTIFICADOR", "consola")