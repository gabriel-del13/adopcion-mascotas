"""Post Confirmation Trigger de Cognito.

Distingue cliente de guardería por el App Client usado en el registro
(`event.callerContext.clientId`, que pone Cognito, no el navegador), asigna
el grupo correspondiente y crea el ítem vacío en la tabla que le toca.

No se le pasan los IDs de App Client como variables de entorno: crearían un
ciclo en el CloudFormation del User Pool (ver el comentario en auth.yaml). En
su lugar se resuelve el nombre del App Client en tiempo de ejecución.
"""
import os
from datetime import date

import boto3

cognito = boto3.client("cognito-idp")
dynamodb = boto3.resource("dynamodb")

TABLA_CATALOGO = os.environ["TABLA_CATALOGO"]
TABLA_SOLICITUDES = os.environ["TABLA_SOLICITUDES"]


def _nombre_app_client(user_pool_id: str, client_id: str) -> str:
    respuesta = cognito.describe_user_pool_client(UserPoolId=user_pool_id, ClientId=client_id)
    return respuesta["UserPoolClient"]["ClientName"]


def lambda_handler(event, context):
    if event["triggerSource"] != "PostConfirmation_ConfirmSignUp":
        return event

    user_pool_id = event["userPoolId"]
    sub = event["request"]["userAttributes"]["sub"]
    email = event["request"]["userAttributes"]["email"]
    hoy = date.today().isoformat()

    nombre_app_client = _nombre_app_client(user_pool_id, event["callerContext"]["clientId"])

    if nombre_app_client.endswith("-guarderia"):
        grupo = "GUARDERIA"
        dynamodb.Table(TABLA_CATALOGO).put_item(
            Item={
                "PK": f"GUARDERIA#{sub}",
                "SK": "METADATA",
                "sub": sub,
                "nombre": email,
                "email": email,
                "telefono": "",
                "ciudad": "",
                "provincia": "",
                "descripcion": "",
                "estado": "pendiente",
                "fechaRegistro": hoy,
                "GSI2PK": "PENDIENTE",
                "GSI2SK": f"FECHA#{hoy}",
            }
        )
    elif nombre_app_client.endswith("-cliente"):
        grupo = "CLIENTE"
        dynamodb.Table(TABLA_SOLICITUDES).put_item(
            Item={
                "PK": f"CLIENTE#{sub}",
                "SK": "METADATA",
                "sub": sub,
                "nombre": email,
                "email": email,
                "telefono": "",
                "fechaRegistro": hoy,
            }
        )
    else:
        # App Client de administración: el ADMIN no se auto-registra por este
        # camino, así que no hay grupo que asignar ni ítem que crear.
        return event

    cognito.admin_add_user_to_group(UserPoolId=user_pool_id, Username=event["userName"], GroupName=grupo)

    return event
