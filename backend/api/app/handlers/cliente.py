"""Entrypoint Lambda: perfil, historial y solicitudes del cliente. JWT +
grupo CLIENTE. Rol IAM: lectura/escritura de su propio ítem y del GSI de
solicitudes por cliente. Ver infra/templates/api.yaml.
"""
from fastapi import FastAPI
from mangum import Mangum

from app.routers import cliente

app = FastAPI(title="Adopción de Mascotas — cliente")
app.include_router(cliente.router)

handler = Mangum(app)
