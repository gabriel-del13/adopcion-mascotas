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
