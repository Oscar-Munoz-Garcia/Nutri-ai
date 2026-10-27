import io
from datetime import date

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from app.main import app
import app.services.sheets_service as sheets_service

client = TestClient(app)


def test_exportar_excel_mensual():
    client.post("/api/v1/diario/consumo", json={
        "nombre": "Avena Export Test", "calorias": 380.0, "proteinas": 13.0,
        "carbohidratos": 60.0, "grasas": 7.0,
    })
    hoy = date.today()
    res = client.get(f"/api/v1/exportar/excel?anio={hoy.year}&mes={hoy.month}")
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]
    wb = load_workbook(io.BytesIO(res.content))
    assert wb.sheetnames == ["Diario", "Despensa", "KPIs & Gráficos"]
    kpis = wb["KPIs & Gráficos"]
    assert len(kpis._charts) == 2
    assert kpis.conditional_formatting
    assert str(kpis["E4"].value).startswith("=IFERROR(AVERAGEIF(")


def test_exportar_excel_mes_invalido():
    res = client.get("/api/v1/exportar/excel?anio=2026&mes=13")
    assert res.status_code == 400


def test_importar_alimentos_csv():
    csv_texto = "Nombre;Cantidad (g);Calorías;Proteínas;Carbohidratos;Grasas\nArroz Import Test;1000;360;7;79;0,6\n;5;1;1;1;1\n"
    res = client.post("/api/v1/importar", files={"file": ("despensa.csv", csv_texto.encode("utf-8"), "text/csv")})
    assert res.status_code == 200
    data = res.json()
    assert data["tipo"] == "alimentos"
    assert data["importados"] + data["actualizados"] == 1
    assert data["errores"][0]["fila"] == 3


def test_importar_recetas_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.append(["nombre", "descripcion", "calorias_totales", "proteinas_totales",
               "carbohidratos_totales", "grasas_totales", "tiempo_preparacion_min", "utensilios"])
    ws.append(["Bowl Import Test", "Arroz con pollo", 550, 45, 60, 12, 20, "Sartén, Olla"])
    buffer = io.BytesIO()
    wb.save(buffer)
    res = client.post("/api/v1/importar", files={"file": ("recetas.xlsx", buffer.getvalue(),
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert res.status_code == 200
    assert res.json()["tipo"] == "recetas"


def test_importar_formato_no_soportado():
    res = client.post("/api/v1/importar", files={"file": ("foto.png", b"123", "image/png")})
    assert res.status_code == 400


def test_sheets_sin_configurar(monkeypatch):
    monkeypatch.delenv("GOOGLE_SHEETS_WEBHOOK_URL", raising=False)
    assert client.get("/api/v1/sheets/estado").json()["configurado"] is False
    assert client.post("/api/v1/sheets/cerrar-jornada").status_code == 503


def test_sheets_envia_resumen(monkeypatch):
    enviados = []

    class RespuestaFalsa:
        status_code = 200

        def json(self):
            return {"ok": True, "fila": 2}

    class ClienteFalso:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json):
            enviados.append((url, json))
            return RespuestaFalsa()

    monkeypatch.setenv("GOOGLE_SHEETS_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")
    monkeypatch.setenv("GOOGLE_SHEETS_WEBHOOK_SECRET", "s3creto")
    monkeypatch.setattr(sheets_service.httpx, "AsyncClient", ClienteFalso)
    res = client.post("/api/v1/sheets/cerrar-jornada")
    assert res.status_code == 200
    url, payload = enviados[0]
    assert payload["secreto"] == "s3creto"
    assert payload["fecha"] == date.today().isoformat()
    assert {"usuario", "calorias", "proteinas", "meta_cumplida"} <= payload.keys()
