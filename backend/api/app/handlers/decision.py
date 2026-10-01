from fastapi import FastAPI
from mangum import Mangum

from app.routers import decision

app = FastAPI(title="Adopción de Mascotas — decisión de solicitud")
app.include_router(decision.router)

handler = Mangum(app)
