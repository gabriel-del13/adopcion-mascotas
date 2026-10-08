"""Tests de integración: corren contra DynamoDB Local real, no mocks.

Requieren 'docker compose up -d' y 'python scripts/tests/seed_test_dynamo.py'
"""
import json as _json
import os
from importlib import import_module
from urllib.parse import urlencode

# Solo se fija aquí, no en app/core/config.py: este módulo es exclusivamente para tests.
os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")

import pytest 

from app.core.auth import requiere_admin, requiere_cliente, requiere_guarderia  

# mismo árbol que infra/templates/api.yaml.
_RUTAS = [
    ("GET", "/animales", "app.handlers.lectura_publica"),
    ("GET", "/animales/{animal_id}", "app.handlers.lectura_publica"),
    ("GET", "/guarderias", "app.handlers.lectura_publica"),
    ("POST", "/solicitudes", "app.handlers.escritura_publica"),
    ("GET", "/cliente/perfil", "app.handlers.cliente"),
    ("PUT", "/cliente/perfil", "app.handlers.cliente"),
    ("GET", "/cliente/solicitudes", "app.handlers.cliente"),
    ("POST", "/cliente/solicitudes", "app.handlers.cliente"),
    ("DELETE", "/cliente", "app.handlers.cliente"),
    ("PUT", "/guarderia/perfil", "app.handlers.guarderia"),
    ("POST", "/guarderias/{guarderia_id}/animales", "app.handlers.guarderia"),
    ("PUT", "/guarderias/{guarderia_id}/animales/{animal_id}", "app.handlers.guarderia"),
    ("DELETE", "/guarderias/{guarderia_id}/animales/{animal_id}", "app.handlers.guarderia"),
    ("POST", "/guarderias/{guarderia_id}/animales/{animal_id}/fotos", "app.handlers.guarderia"),
    ("GET", "/guarderias/{guarderia_id}/solicitudes", "app.handlers.guarderia"),
    ("POST", "/guarderias/{guarderia_id}/solicitudes/{animal_id}/aceptar", "app.handlers.guarderia"),
    ("POST", "/guarderias/{guarderia_id}/solicitudes/{animal_id}/rechazar", "app.handlers.guarderia"),
    ("GET", "/admin/guarderias/pendientes", "app.handlers.admin"),
    ("POST", "/admin/guarderias/{sub}/aprobar", "app.handlers.admin"),
    ("POST", "/admin/guarderias/{sub}/rechazar", "app.handlers.admin"),
    ("GET", "/decision", "app.handlers.decision"),
    ("POST", "/decision", "app.handlers.decision"),
]

_GRUPOS = {requiere_cliente: "CLIENTE", requiere_guarderia: "GUARDERIA", requiere_admin: "ADMIN"}


def _resolver(metodo: str, path: str):
    segmentos_path = [s for s in path.split("/") if s]
    for m, plantilla, modulo in _RUTAS:
        if m != metodo:
            continue
        segmentos_plantilla = [s for s in plantilla.split("/") if s]
        if len(segmentos_plantilla) != len(segmentos_path):
            continue
        params, coincide = {}, True
        for sp, sv in zip(segmentos_plantilla, segmentos_path):
            if sp.startswith("{") and sp.endswith("}"):
                params[sp[1:-1]] = sv
            elif sp != sv:
                coincide = False
                break
        if coincide:
            return modulo, plantilla, (params or None)
    raise AssertionError(f"Ninguna ruta de prueba coincide con {metodo} {path}")


class _Respuesta:
    def __init__(self, crudo: dict):
        self.status_code = crudo["statusCode"]
        self._body = crudo.get("body") or ""

    def json(self):
        return _json.loads(self._body)

    @property
    def text(self):
        return self._body


class _ClienteFalso:
    def __init__(self, estado_auth: dict):
        self._estado = estado_auth

    def _peticion(self, metodo: str, path: str, *, json=None, data=None, params=None) -> _Respuesta:
        modulo, recurso, path_params = _resolver(metodo, path)
        if json is not None:
            cuerpo = _json.dumps(json)
        elif data is not None:
            cuerpo = urlencode(data)
        else:
            cuerpo = None

        claims = self._estado["claims"]
        evento = {
            "httpMethod": metodo,
            "resource": recurso,
            "path": path,
            "pathParameters": path_params,
            "queryStringParameters": params,
            "body": cuerpo,
            "isBase64Encoded": False,
            "requestContext": {"authorizer": {"claims": claims}} if claims else {},
        }
        respuesta = import_module(modulo).handler(evento, {})
        return _Respuesta(respuesta)

    def get(self, path, params=None):
        return self._peticion("GET", path, params=params)

    def post(self, path, json=None, data=None, params=None):
        return self._peticion("POST", path, json=json, data=data, params=params)

    def put(self, path, json=None, params=None):
        return self._peticion("PUT", path, json=json, params=params)

    def delete(self, path, params=None):
        return self._peticion("DELETE", path, params=params)


@pytest.fixture
def _estado_auth():
    return {"claims": None}


@pytest.fixture
def cliente(_estado_auth) -> _ClienteFalso:
    return _ClienteFalso(_estado_auth)


@pytest.fixture
def autenticar(_estado_auth):

    def _autenticar(dependencia, sub: str) -> None:
        _estado_auth["claims"] = {"sub": sub, "cognito:groups": _GRUPOS[dependencia]}

    return _autenticar
