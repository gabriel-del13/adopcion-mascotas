"""Entrypoint Lambda: gestión de animales por la guardería. JWT + grupo
GUARDERIA (la aprobación se comprueba en el código). Rol IAM: escritura en
catalogo, lectura del GSI de solicitudes por guardería. Ver
infra/templates/api.yaml.
"""
from fastapi import FastAPI
from mangum import Mangum

from app.routers import guarderia

app = FastAPI(title="Adopción de Mascotas — guardería")
app.include_router(guarderia.router)

handler = Mangum(app)
