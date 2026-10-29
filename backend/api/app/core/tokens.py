"""Token de un solo uso para los enlaces de decisión por correo (aceptar /
rechazar una solicitud sin login).
"""
import hashlib
import hmac
import secrets


def generar_token() -> tuple[str, str]:
    """Token aleatorio de 256 bits y su hash SHA-256. Solo el hash se guarda
    en DynamoDB; el token en claro viaja únicamente en el mensaje de SQS."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def verificar_token(token: str, token_hash: str) -> bool:
    """Comparación en tiempo constante: comparar hashes con `==` filtraría
    por temporización cuánto del hash coincide."""
    return hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), token_hash)
