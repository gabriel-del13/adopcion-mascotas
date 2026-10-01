"""Alta, edición y baja de animales por una guardería aprobada, gestión del
perfil propio y de las solicitudes recibidas.
"""
from unittest.mock import patch

from app.core import repositorio_catalogo as repo_directo
from app.core.auth import requiere_guarderia
from app.models.animal import Animal


def test_crear_animal_como_guarderia_aprobada(cliente, autenticar):
    autenticar(requiere_guarderia, "g1")
    respuesta = cliente.post(
        "/guarderias/g1/animales",
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


def test_actualizar_perfil_guarderia(cliente, autenticar):
    autenticar(requiere_guarderia, "g1")
    respuesta = cliente.put(
        "/guarderia/perfil",
        json={
            "nombre": "Huellas Felices (renombrada)",
            "telefono": "600999888",
            "ciudad": "Alcalá de Henares",
            "provincia": "Madrid",
            "descripcion": "Descripción actualizada.",
        },
    )

    assert respuesta.status_code == 200
    perfil = respuesta.json()
    assert perfil["nombre"] == "Huellas Felices (renombrada)"
    assert perfil["ciudad"] == "Alcalá de Henares"
    # El estado (aprobada/pendiente) no lo puede tocar la propia guardería por aquí.
    assert perfil["estado"] == "aprobada"


def _crear_animal_de_prueba(cliente, autenticar, **overrides) -> dict:
    autenticar(requiere_guarderia, "g1")
    datos = {
        "nombre": "Provisional", "tipo": "perro", "edad": "adulto",
        "ciudad": "Madrid", "provincia": "Madrid", "descripcion": "Animal creado para un test.",
    }
    datos.update(overrides)
    return cliente.post("/guarderias/g1/animales", json=datos).json()


def test_editar_animal(cliente, autenticar):
    creado = _crear_animal_de_prueba(cliente, autenticar)

    respuesta = cliente.put(
        f"/guarderias/g1/animales/{creado['id']}",
        json={
            "nombre": "Editado",
            "tipo": "perro",
            "edad": "adulto",
            "estado": "no_disponible",
            "ciudad": "Madrid",
            "provincia": "Madrid",
            "descripcion": "En revisión veterinaria.",
        },
    )

    assert respuesta.status_code == 200
    animal = respuesta.json()
    assert animal["nombre"] == "Editado"
    assert animal["estado"] == "no_disponible"

    # Al dejar de estar "disponible" ya no sale en el listado público por defecto.
    listado = cliente.get("/animales").json()
    assert not any(a["id"] == creado["id"] for a in listado)

def test_eliminar_animal(cliente, autenticar):
    autenticar(requiere_guarderia, "g1")
    creado = cliente.post(
        "/guarderias/g1/animales",
        json={
            "nombre": "Temporal", "tipo": "gato", "edad": "adulto",
            "ciudad": "Madrid", "provincia": "Madrid", "descripcion": "Se borra en el test.",
        },
    ).json()

    respuesta = cliente.delete(f"/guarderias/g1/animales/{creado['id']}")
    assert respuesta.status_code == 204
    assert cliente.get(f"/animales/{creado['id']}").status_code == 404

def test_aceptar_solicitud_marca_animal_en_proceso(cliente, autenticar):
    animal = _crear_animal_de_prueba(cliente, autenticar, nombre="Para aceptar")
    solicitud = cliente.post(
        "/solicitudes",
        json={
            "animalId": animal["id"],
            "nombre": "Otro Interesado",
            "email": "otro@ejemplo.com",
            "telefono": "699333444",
            "mensaje": "Me gustaría adoptarlo.",
        },
    ).json()

    autenticar(requiere_guarderia, "g1")
    respuesta = cliente.post(f"/guarderias/g1/solicitudes/{animal['id']}/aceptar", params={"fecha": solicitud["fecha"]})
    assert respuesta.status_code == 204
    assert cliente.get(f"/animales/{animal['id']}").json()["estado"] == "en_proceso"

    # Ya no está pendiente: aceptarla otra vez no debe volver a aplicar el cambio.
    repetir = cliente.post(f"/guarderias/g1/solicitudes/{animal['id']}/aceptar", params={"fecha": solicitud["fecha"]})
    assert repetir.status_code == 409


def test_subir_foto_devuelve_presignada_con_clave_correcta(cliente, autenticar):
    animal = _crear_animal_de_prueba(cliente, autenticar, nombre="Con fotos")

    with patch("app.routers.guarderia.s3.generate_presigned_post") as generar:
        generar.return_value = {"url": "https://bucket.s3.amazonaws.com", "fields": {"key": "campo-de-prueba"}}
        respuesta = cliente.post(
            f"/guarderias/g1/animales/{animal['id']}/fotos",
            json={"contentType": "image/jpeg"},
        )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["fotoId"]
    assert cuerpo["url"] == "https://bucket.s3.amazonaws.com"

    llamada = generar.call_args.kwargs
    assert llamada["Key"] == f"animales/g1/{animal['id']}/{cuerpo['fotoId']}"
    assert llamada["Fields"]["Content-Type"] == "image/jpeg"
