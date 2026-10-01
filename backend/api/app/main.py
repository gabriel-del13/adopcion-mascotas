"""App combinada con todos los routers, para desarrollo local con uvicorn y
para los tests. En AWS no se despliega esta app: se despliegan las cinco de
app/handlers/, cada una con solo su router y su rol IAM. Ver
infra/templates/api.yaml.
"""
import os

'''
# Solo se fija aquí, no en app/core/config.py: este módulo es exclusivamente para uvicorn local y tests. 
Las Lambdas reales importan app/handlers/*, no este fichero, así que nunca heredan este valor por defecto — 
apuntar a DynamoDB Local desde una Lambda de verdad se queda colgado hasta el timeout, porque ahí no hay nada escuchando en ese puerto.

'''
os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")

from fastapi import FastAPI  # noqa: E402

from app.routers import admin, cliente, decision, guarderia, publico, solicitudes  # noqa: E402

app = FastAPI(title="Adopción de Mascotas")

app.include_router(publico.router)
app.include_router(solicitudes.router)
app.include_router(cliente.router)
app.include_router(guarderia.router)
app.include_router(admin.router)
app.include_router(decision.router)
