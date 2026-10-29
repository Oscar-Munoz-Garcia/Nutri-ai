from fastapi.testclient import TestClient
from app.main import app
import app.services.agent_service as agent_service
import app.services.quicklog_service as quicklog_service

client = TestClient(app)


def test_pagina_carga_el_selector_de_idioma():
    html = client.get("/").text
    assert '<script src="/static/i18n.js"></script>' in html
    assert html.count("data-selector-idioma") >= 4  # cabecera, acceso, aviso de primera vez y cuestionario
    script = client.get("/static/i18n.js")
    assert script.status_code == 200
    assert "alternarIdioma" in script.text


def test_agente_responde_en_el_idioma_elegido(monkeypatch):
    monkeypatch.setattr(agent_service.settings, "GROQ_API_KEY", None)
    historial = [{"role": "user", "content": "hola"}]
    en = client.post("/api/v1/chat/planificar", json={"historial": historial, "idioma": "en"}).json()
    es = client.post("/api/v1/chat/planificar", json={"historial": historial}).json()
    assert en["respuesta"].startswith("Set GROQ_API_KEY")
    assert es["respuesta"].startswith("Configura GROQ_API_KEY")


def test_registro_rapido_entiende_frases_en_ingles():
    comida, resto = quicklog_service.separar_comida("Breakfast: 3 boiled eggs and 80g of oats")
    assert comida == "Breakfast"
    assert quicklog_service.separar_alimentos(resto) == ["3 boiled eggs", "80g of oats"]
