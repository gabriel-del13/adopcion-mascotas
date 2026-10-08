"""Lectura de los claims de Cognito ya validados por el Authorizer nativo
COGNITO_USER_POOLS de API Gateway.

El Authorizer valida la firma y la expiración del token antes de invocar la
Lambda: aquí solo se leen los claims, nunca se vuelve a verificar el JWT.
"""
from app.core.respuestas import ApiError


def obtener_claims(event: dict) -> dict:
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims")
    if not claims:
        raise ApiError(401, "No hay un token válido en la petición")
    return claims


def obtener_sub(event: dict) -> str:
    return obtener_claims(event)["sub"]


def requerir_grupo(grupo: str):
    """Exige que 'grupo' esté en 'cognito:groups'.

    IAM solo llega hasta la tabla y el índice; que el usuario pertenezca al
    grupo correcto para ESTE recurso concreto.

    El Authorizer entrega 'cognito:groups' como un string separado por comas 
    sin corchetes ("GRUPO1,GRUPO2").
    """

    def dependencia(event: dict) -> str:
        claims = obtener_claims(event)
        grupos = [g.strip() for g in claims.get("cognito:groups", "").split(",") if g.strip()]
        if grupo not in grupos:
            raise ApiError(403, f"Requiere el grupo {grupo}")
        return claims["sub"]

    return dependencia


requiere_cliente = requerir_grupo("CLIENTE")
requiere_guarderia = requerir_grupo("GUARDERIA")
requiere_admin = requerir_grupo("ADMIN")
