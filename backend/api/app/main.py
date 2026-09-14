from fastapi import FastAPI

from app.routers import guarderia, publico, solicitudes

app = FastAPI(title="Adopción de Mascotas")

app.include_router(publico.router)
app.include_router(solicitudes.router)
app.include_router(guarderia.router)

# MVP: en producción esto se despliega en Lambda envuelto con Mangum:
# from mangum import Mangum
# handler = Mangum(app)
