# NutriAI Studio — Guía de Desarrollo

## Comandos Principales
- Activar entorno: `.venv\Scripts\activate`
- Iniciar servidor: `uvicorn app.main:app --reload`
- Ejecutar tests: `pytest -v`
- Reiniciar BD SQLite: `del nutri_ai.db`

## Stack Tecnológico
- Backend: Python 3.11, FastAPI, SQLAlchemy (SQLite `nutri_ai.db`), Pydantic v2.
- Seguridad: PyJWT, Passlib con `bcrypt==4.0.1` (versión fija necesaria).
- Frontend: Single Page Application en `app/templates/index.html` (Tailwind CSS dark mode, Vanilla JS, Chart.js).
- Visión IA: Groq Vision API.

## Reglas de Código
- Todas las rutas `fetch` en JavaScript usan `API_BASE = "/api/v1"` e incluyen la cabecera JWT `Authorization: Bearer <token>`.
- La columna `usuario_id` en `PerfilDB` debe mantenerse como `nullable=True`.
- Los 10 tests en `tests/test_main.py` deben dar siempre 100% `PASSED`.