"""Caminos positivos del catálogo público. Usa los datos sembrados por
scripts/tests/seed_test_dynamo.py: animal a1 (perro, adulto, disponible,
de la guardería g1), guarderías g1 y g2 aprobadas, g3 pendiente.
"""


def test_listar_animales_disponibles(cliente):
    respuesta = cliente.get("/animales")

    assert respuesta.status_code == 200
    animales = respuesta.json()
    assert any(a["id"] == "a1" for a in animales)
    assert all(a["estado"] == "disponible" for a in animales)


def test_obtener_ficha_de_animal(cliente):
    respuesta = cliente.get("/animales/a1")

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Rex"


def test_listar_guarderias_aprobadas(cliente):
    respuesta = cliente.get("/guarderias")

    assert respuesta.status_code == 200
    subs = [g["sub"] for g in respuesta.json()]
    assert "g1" in subs
    assert "g3" not in subs
