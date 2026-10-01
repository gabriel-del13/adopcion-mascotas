"""
Lectura de los claims de Cognito ya validados por el JWT Authorizer de
API Gateway.

El Authorizer valida la firma y la expiración del token antes de invocar la
Lambda: aquí solo se leen los claims, nunca se vuelve a verificar el JWT.
Mangum expone el evento original de API Gateway en `request.scope["aws.event"]`;
de ahí sale `requestContext.authorizer.jwt.claims`.
"""
from fastapi import HTTPException, Request


def obtener_claims(request: Request) -> dict:
    evento = request.scope.get("aws.event", {})
    claims = evento.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims")
    if not claims:
        raise HTTPException(status_code=401, detail="No hay un token válido en la petición")
    return claims


def obtener_sub(request: Request) -> str:
    return obtener_claims(request)["sub"]


def requerir_grupo(grupo: str):
    """Factoría de dependencias: exige que `grupo` esté en `cognito:groups`.

    IAM solo llega hasta la tabla y el índice; que el usuario pertenezca al
    grupo correcto para ESTE recurso concreto lo comprueba el código, no IAM.
    """

    def dependencia(request: Request) -> str:
        claims = obtener_claims(request)
        grupos = claims.get("cognito:groups", [])
        # El JWT Authorizer de API Gateway convierte el claim de lista a un
        # string con la notación "[GRUPO1, GRUPO2]" (no CSV ni separado por
        # espacios), así que hay que quitar los corchetes antes de separar.
        if isinstance(grupos, str):
            grupos = [g.strip() for g in grupos.strip("[]").split(",") if g.strip()]
        if grupo not in grupos:
            raise HTTPException(status_code=403, detail=f"Requiere el grupo {grupo}")
        return claims["sub"]

    return dependencia


requiere_cliente = requerir_grupo("CLIENTE")
requiere_guarderia = requerir_grupo("GUARDERIA")
requiere_admin = requerir_grupo("ADMIN")
