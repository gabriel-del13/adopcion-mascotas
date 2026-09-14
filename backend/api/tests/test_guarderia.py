"""Camino positivo del alta de animal por una guardería aprobada."""


def test_crear_animal_como_guarderia_aprobada(cliente):
    respuesta = cliente.post(
        "/guarderias/g1/animales",
        headers={"X-Usuario-Simulado": "g1"},
        json={
            "nombre": "Nube",
            "tipo": "perro",
            "edad": "cachorro",
            "ciudad": "Madrid",
            "provincia": "Madrid",
            "descripcion": "Cachorra encontrada en un parque, muy sociable.",
        },
    )

    assert respuesta.status_code == 201
    animal = respuesta.json()
    assert animal["guarderiaId"] == "g1"
    assert animal["estado"] == "disponible"
    assert animal["id"]

    ficha = cliente.get(f"/animales/{animal['id']}")
    assert ficha.status_code == 200
    assert ficha.json()["nombre"] == "Nube"
