"""Entrypoint Lambda: catálogo público. Sin autenticación, solo lectura.
Rol IAM: Query/GetItem/Scan sobre la tabla catalogo. Ver infra/templates/api.yaml.
"""
from fastapi import FastAPI
from mangum import Mangum

from app.routers import publico

app = FastAPI(title="Adopción de Mascotas — lectura pública")
app.include_router(publico.router)

handler = Mangum(app)
