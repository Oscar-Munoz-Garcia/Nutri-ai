from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.models.user import PerfilUsuario, ObjetivoMacros
from app.services.macro_service import calcular_objetivo_macros

app = FastAPI(title=settings.PROJECT_NAME)


@app.get("/", include_in_schema=False)
def inicio():
    """Redirige la raíz a la documentación Swagger."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {
        "estado": "ok",
        "proyecto": settings.PROJECT_NAME,
        "entorno": settings.ENVIRONMENT
    }


@app.post("/api/v1/macros/calcular", response_model=ObjetivoMacros)
def calcular_macros(perfil: PerfilUsuario):
    """
    Calcula el BMR, TDEE, calorías diarias y reparto de macronutrientes objetivo
    a partir del perfil antropométrico del usuario.
    """
    return calcular_objetivo_macros(perfil)