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
    def dependencia(request: Request) -> str:
        claims = obtener_claims(request)
        grupos = claims.get("cognito:groups", [])
        if isinstance(grupos, str):
            grupos = [g.strip() for g in grupos.strip("[]").split(",") if g.strip()]
        if grupo not in grupos:
            raise HTTPException(status_code=403, detail=f"Requiere el grupo {grupo}")
        return claims["sub"]

    return dependencia


requiere_cliente = requerir_grupo("CLIENTE")
requiere_guarderia = requerir_grupo("GUARDERIA")
requiere_admin = requerir_grupo("ADMIN")
