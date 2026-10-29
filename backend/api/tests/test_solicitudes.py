"""Camino positivo del formulario anónimo de interés."""


def test_crear_solicitud_anonima(cliente):
    respuesta = cliente.post(
        "/solicitudes",
        json={
            "animalId": "a1",
            "nombre": "Laura Prueba",
            "email": "laura@ejemplo.com",
            "telefono": "699000111",
            "mensaje": "Quiero adoptar a Rex.",
        },
    )

    assert respuesta.status_code == 201
    solicitud = respuesta.json()
    assert solicitud["animalId"] == "a1"
    assert solicitud["guarderiaId"] == "g1"
    assert solicitud["clienteId"] is None
    assert solicitud["estado"] == "pendiente"
