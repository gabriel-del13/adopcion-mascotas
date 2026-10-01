"""Tests de integración: corren contra DynamoDB Local real, no mocks.

Requieren `docker compose up -d` y `python scripts/tests/seed_test_dynamo.py`
ya ejecutados (los mismos datos de prueba que se usan para probar a mano).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(app)


@pytest.fixture
def autenticar():
    """Sustituye una dependencia de auth (requiere_cliente, requiere_guarderia,
    requiere_admin...) por un sub fijo.

    No hay cabecera simulada que enviar: en AWS los claims los pone el JWT
    Authorizer de API Gateway antes de invocar la Lambda, así que el test
    reemplaza directamente la dependencia de FastAPI, igual que se reemplazaría
    en producción si algún día hubiera que mockear el authorizer.
    """
    def _autenticar(dependencia, sub: str) -> None:
        app.dependency_overrides[dependencia] = lambda: sub

    yield _autenticar
    app.dependency_overrides.clear()
