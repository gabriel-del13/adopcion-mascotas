"""Entrypoint Lambda: aprobación de guarderías. JWT + grupo ADMIN. Rol IAM:
Query sobre el GSI de guarderías pendientes, UpdateItem en catalogo. Ver
infra/templates/api.yaml.
"""
from fastapi import FastAPI
from mangum import Mangum

from app.routers import admin

app = FastAPI(title="Adopción de Mascotas — administración")
app.include_router(admin.router)

handler = Mangum(app)
