from fastapi import FastAPI

from app.routers import publico, solicitudes

app = FastAPI(title="Adopción de Mascotas")

app.include_router(publico.router)
app.include_router(solicitudes.router)

# MVP: en producción esto se despliega en Lambda envuelto con Mangum:
# from mangum import Mangum
# handler = Mangum(app)
