"""Perfil, historial y borrado de cuenta del cliente. Usa el cliente c1
sembrado por scripts/tests/seed_test_dynamo.py.
"""
from unittest.mock import patch

from app.core.auth import requiere_cliente


def test_obtener_perfil(cliente, autenticar):
    autenticar(requiere_cliente, "c1")
    respuesta = cliente.get("/cliente/perfil")

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Marcos Abad"


def test_perfil_inexistente(cliente, autenticar):
    autenticar(requiere_cliente, "sin-ficha")
    assert cliente.get("/cliente/perfil").status_code == 404


def test_actualizar_perfil_y_crear_solicitud_con_sesion(cliente, autenticar):
    autenticar(requiere_cliente, "c1")
    actualizado = cliente.put(
        "/cliente/perfil",
        json={"nombre": "Marcos A.", "telefono": "611000000", "descripcionSituacion": "Piso con jardín."},
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["descripcionSituacion"] == "Piso con jardín."

    solicitud = cliente.post("/cliente/solicitudes", json={"animalId": "a1", "mensaje": "Me interesa."})
    assert solicitud.status_code == 201
    cuerpo = solicitud.json()
    assert cuerpo["clienteId"] == "c1"
    assert cuerpo["descripcionSituacion"] == "Piso con jardín."

    historial = cliente.get("/cliente/solicitudes").json()
    assert any(s["animalId"] == "a1" for s in historial)

def test_borrar_cuenta_borra_perfil_y_solicitudes_antes_que_cognito(cliente, autenticar):
    autenticar(requiere_cliente, "c2")
    # Deja una solicitud propia para comprobar que el borrado también la alcanza.
    cliente.post("/cliente/solicitudes", json={"animalId": "a6", "mensaje": "Interesada en Mia."})

    with patch("app.routers.cliente.cognito.admin_delete_user") as admin_delete_user:
        respuesta = cliente.delete("/cliente")

    assert respuesta.status_code == 204
    admin_delete_user.assert_called_once()
    assert admin_delete_user.call_args.kwargs["Username"] == "c2"

    # El perfil ya no existe: comprobarlo con otra petición autenticada como c2.
    assert cliente.get("/cliente/perfil").status_code == 404
    assert cliente.get("/cliente/solicitudes").json() == []
