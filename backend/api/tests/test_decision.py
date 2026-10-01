"""Enlaces de decisión por correo: aceptar/rechazar una solicitud con el
token de un solo uso, sin login. NOTIFICADOR sigue en "consola" en tests
(igual que en local), así que el token en claro se captura de lo que imprime
`NotificadorConsola` - nunca vuelve en una respuesta HTTP (ver
response_model_exclude en los routers de solicitudes).
"""
import re
from urllib.parse import parse_qs, urlparse

from app.core.auth import requiere_cliente, requiere_guarderia

_RE_ENLACE = re.compile(r"(Aceptar|Rechazar): (\S+)")


def _crear_animal(cliente, autenticar, **overrides) -> dict:
    autenticar(requiere_guarderia, "g1")
    datos = {
        "nombre": "Provisional", "tipo": "perro", "edad": "adulto",
        "ciudad": "Madrid", "provincia": "Madrid", "descripcion": "Animal para test de decisión.",
    }
    datos.update(overrides)
    return cliente.post("/guarderias/g1/animales", json=datos).json()


def _enlaces_desde_salida(salida: str) -> dict[str, str]:
    return dict(_RE_ENLACE.findall(salida))


def _crear_solicitud_anonima_y_capturar_enlaces(cliente, capsys, animal_id: str) -> tuple[dict, dict[str, str]]:
    respuesta = cliente.post(
        "/solicitudes",
        json={
            "animalId": animal_id,
            "nombre": "Interesado Decisión",
            "email": "decision@ejemplo.com",
            "telefono": "699000000",
            "mensaje": "Quiero adoptarlo.",
        },
    )
    assert respuesta.status_code == 201
    salida = capsys.readouterr().out
    return respuesta.json(), _enlaces_desde_salida(salida)


def _params_de(enlace: str) -> dict[str, str]:
    query = parse_qs(urlparse(enlace).query)
    return {clave: valores[0] for clave, valores in query.items()}


def test_hash_del_token_nunca_sale_en_la_respuesta_http(cliente, autenticar, capsys):
    animal = _crear_animal(cliente, autenticar, nombre="Sin hash expuesto")
    solicitud, _ = _crear_solicitud_anonima_y_capturar_enlaces(cliente, capsys, animal["id"])
    assert "tokenHash" not in solicitud
    assert "tokenExpira" not in solicitud


def test_get_decision_con_token_valido_muestra_confirmacion(cliente, autenticar, capsys):
    animal = _crear_animal(cliente, autenticar, nombre="Para confirmar")
    _, enlaces = _crear_solicitud_anonima_y_capturar_enlaces(cliente, capsys, animal["id"])

    respuesta = cliente.get("/decision", params=_params_de(enlaces["Aceptar"]))
    assert respuesta.status_code == 200
    assert "Confirmar" in respuesta.text


def test_get_decision_con_token_invalido_rechaza(cliente, autenticar, capsys):
    animal = _crear_animal(cliente, autenticar, nombre="Token incorrecto")
    _, enlaces = _crear_solicitud_anonima_y_capturar_enlaces(cliente, capsys, animal["id"])

    params = _params_de(enlaces["Aceptar"])
    params["token"] = "token-que-no-corresponde"
    respuesta = cliente.get("/decision", params=params)
    assert respuesta.status_code == 403


def test_aceptar_por_decision_marca_animal_en_proceso_y_es_de_un_solo_uso(cliente, autenticar, capsys):
    animal = _crear_animal(cliente, autenticar, nombre="Para aceptar por correo")
    _, enlaces = _crear_solicitud_anonima_y_capturar_enlaces(cliente, capsys, animal["id"])
    params = _params_de(enlaces["Aceptar"])

    respuesta = cliente.post("/decision", data=params)
    assert respuesta.status_code == 200
    assert cliente.get(f"/animales/{animal['id']}").json()["estado"] == "en_proceso"

    repetir = cliente.post("/decision", data=params)
    assert repetir.status_code == 410


def test_rechazar_anonima_por_decision_borra_la_solicitud_y_cuenta_el_rechazo(cliente, autenticar, capsys):
    animal = _crear_animal(cliente, autenticar, nombre="Para rechazar por correo")
    _, enlaces = _crear_solicitud_anonima_y_capturar_enlaces(cliente, capsys, animal["id"])
    params = _params_de(enlaces["Rechazar"])

    respuesta = cliente.post("/decision", data=params)
    assert respuesta.status_code == 200
    assert cliente.get(f"/animales/{animal['id']}").json()["contadorRechazosAnonimos"] == 1

    # Borrada: el mismo enlace ya no encuentra la solicitud.
    repetir = cliente.post("/decision", data=params)
    assert repetir.status_code == 410


def test_rechazar_solicitud_de_cliente_por_decision_conserva_historial_sin_datos_de_contacto(cliente, autenticar, capsys):
    animal = _crear_animal(cliente, autenticar, nombre="Para rechazar (con cliente)")

    autenticar(requiere_cliente, "c1")
    respuesta = cliente.post("/cliente/solicitudes", json={"animalId": animal["id"], "mensaje": "Me interesa."})
    assert respuesta.status_code == 201
    salida = capsys.readouterr().out
    enlaces = _enlaces_desde_salida(salida)

    decision = cliente.post("/decision", data=_params_de(enlaces["Rechazar"]))
    assert decision.status_code == 200

    historial = cliente.get("/cliente/solicitudes").json()
    propia = next(s for s in historial if s["animalId"] == animal["id"])
    assert propia["estado"] == "rechazada"
    assert "nombre" not in propia or propia["nombre"] is None
