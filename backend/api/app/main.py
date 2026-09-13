from fastapi import FastAPI

from app.routers import publico

app = FastAPI(title="Adopción de Mascotas")

app.include_router(publico.router)

# MVP: en producción esto se despliega en Lambda envuelto con Mangum:
# from mangum import Mangum
# handler = Mangum(app)
