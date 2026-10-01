"""Auth simulada por cabecera HTTP para el MVP.

# MVP: en producción esto lo valida el JWT Authorizer de API Gateway a partir
del token de Cognito, y aquí solo se leería el claim `sub` ya verificado.
"""
from fastapi import Header, HTTPException


def obtener_sub_autenticado(x_usuario_simulado: str | None = Header(default=None)) -> str:
    if not x_usuario_simulado:
        raise HTTPException(status_code=401, detail="Falta la cabecera X-Usuario-Simulado")
    return x_usuario_simulado
