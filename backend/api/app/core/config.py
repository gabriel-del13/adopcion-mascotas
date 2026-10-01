"""Configuración de entorno para la capa de acceso a datos.

En AWS estos valores los pone CloudFormation como variables de entorno de la
Lambda (ver infra/templates/api.yaml y auth.yaml), a partir de los Outputs de
dynamodb.yaml. En local, los valores por defecto apuntan a DynamoDB Local.
"""
import os

REGION = os.environ.get("AWS_REGION", "eu-west-1")
# None en AWS (endpoint real de DynamoDB); solo se fija en local, vía docker-compose.
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL")
TABLA_CATALOGO = os.environ.get("TABLA_CATALOGO", "adopcion-mascotas-local-catalogo")
TABLA_SOLICITUDES = os.environ.get("TABLA_SOLICITUDES", "adopcion-mascotas-local-solicitudes")
NOTIFICADOR = os.environ.get("NOTIFICADOR", "consola")
# Solo si NOTIFICADOR=sqs: URL de la cola de infra/templates/notificaciones.yaml.
COLA_NOTIFICACIONES_URL = os.environ.get("COLA_NOTIFICACIONES_URL")
# Buckets de infra/templates/fotos.yaml. None en local: sin AWS real no hay
# presignadas que probar (ver Pruebas_Manuales.md).
BUCKET_FOTOS_ORIGINALES = os.environ.get("BUCKET_FOTOS_ORIGINALES")
BUCKET_FOTOS_DERIVADAS = os.environ.get("BUCKET_FOTOS_DERIVADAS")
# Base para los enlaces de decisión por correo (aceptar/rechazar), p. ej.
# https://<api-id>.execute-api.eu-west-1.amazonaws.com. En local, la propia
# API de uvicorn.
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
# Solo lo usa app/routers/cliente.py (borrado de cuenta, AdminDeleteUser). En
# local no hay Cognito real, así que ese endpoint no se puede probar contra uvicorn
USER_POOL_ID = os.environ.get("USER_POOL_ID")