"""Aprobación de guarderías por el administrador. g3 (sembrada por
scripts/tests/seed_test_dynamo.py) se deja pendiente a propósito para que
test_publico.py pueda seguir comprobando que no aparece en /guarderias: los
tests de aquí crean su propia guardería pendiente en vez de tocarla.
"""
from datetime import date

from app.core.auth import requiere_admin
from app.core.repositorio_catalogo import crear_guarderia
from app.models.guarderia import EstadoGuarderia, Guarderia


def _crear_guarderia_pendiente(sub: str) -> None:
    crear_guarderia(
        Guarderia(
            sub=sub,
            nombre=f"Guardería de prueba {sub}",
            email=f"{sub}@ejemplo.com",
            estado=EstadoGuarderia.pendiente,
            fechaRegistro=date.today(),
        )
    )


def test_listar_pendientes(cliente, autenticar):
    _crear_guarderia_pendiente("g-test-pendiente-1")
    autenticar(requiere_admin, "admin")
    pendientes = cliente.get("/admin/guarderias/pendientes").json()

    assert any(g["sub"] == "g-test-pendiente-1" for g in pendientes)
    assert not any(g["sub"] in ("g1", "g2") for g in pendientes)


def test_aprobar_guarderia(cliente, autenticar):
    _crear_guarderia_pendiente("g-test-pendiente-2")
    autenticar(requiere_admin, "admin")
    respuesta = cliente.post("/admin/guarderias/g-test-pendiente-2/aprobar")

    assert respuesta.status_code == 204
    subs_aprobadas = [g["sub"] for g in cliente.get("/guarderias").json()]
    assert "g-test-pendiente-2" in subs_aprobadas

    pendientes = cliente.get("/admin/guarderias/pendientes").json()
    assert not any(g["sub"] == "g-test-pendiente-2" for g in pendientes)


def test_rechazar_guarderia(cliente, autenticar):
    _crear_guarderia_pendiente("g-test-pendiente-3")
    autenticar(requiere_admin, "admin")
    respuesta = cliente.post("/admin/guarderias/g-test-pendiente-3/rechazar", json={"motivo": "Documentación incompleta"})

    assert respuesta.status_code == 204
    pendientes = cliente.get("/admin/guarderias/pendientes").json()
    assert not any(g["sub"] == "g-test-pendiente-3" for g in pendientes)


def test_rechazar_guarderia_inexistente(cliente, autenticar):
    autenticar(requiere_admin, "admin")
    respuesta = cliente.post("/admin/guarderias/no-existe/rechazar", json={"motivo": "No existe"})

    assert respuesta.status_code == 404
