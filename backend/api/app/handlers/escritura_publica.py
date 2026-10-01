"""Entrypoint Lambda: alta anónima de solicitudes de interés. Sin
autenticación (la protección de esta ruta es WAF, fase pendiente). Rol IAM:
solo PutItem en la tabla solicitudes, GetItem/Query en catalogo. Ver
infra/templates/api.yaml.
"""
from fastapi import FastAPI
from mangum import Mangum

from app.routers import solicitudes

app = FastAPI(title="Adopción de Mascotas — escritura pública")
app.include_router(solicitudes.router)

handler = Mangum(app)
