"""Exportador mensual a Excel (.xlsx) con pestañas Diario, Despensa y KPIs."""
import calendar
from datetime import date
from io import BytesIO
from typing import Dict, List, Optional

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from app.db.session import SessionLocal
from app.db.models import PantryDB, PerfilDB, RegistroConsumoDB

# Paleta del reporte (tonos suaves, coherentes con la app)
COLOR_CABECERA = "4981D4"
COLOR_TITULO = "5749D4"
FILL_OK = PatternFill("solid", start_color="C8EFD4", end_color="C8EFD4")
FILL_AVISO = PatternFill("solid", start_color="FCE8B2", end_color="FCE8B2")
FILL_MAL = PatternFill("solid", start_color="F6C9C9", end_color="F6C9C9")
FONT_OK = Font(color="1E6B3A")
FONT_AVISO = Font(color="7A5A00")
FONT_MAL = Font(color="8A1F1F")

BORDE_FINO = Border(bottom=Side(style="thin", color="D6D6D6"))

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _metas_usuario(db, usuario_id: int) -> Dict[str, float]:
    pdb = db.query(PerfilDB).filter(PerfilDB.usuario_id == usuario_id).first()
    pdb = pdb or PerfilDB()
    return {
        "calorias": pdb.calorias_objetivo or 2200.0,
        "proteinas": pdb.proteinas_objetivo or 160.0,
        "carbohidratos": pdb.carbohidratos_objetivo or 210.0,
        "grasas": pdb.grasas_objetivo or 70.0,
    }


def resumen_dia(usuario_id: int, fecha: Optional[str] = None) -> Dict:
    """Totales y cumplimiento de un día concreto para un usuario."""
    fecha = fecha or date.today().isoformat()
    db = SessionLocal()
    try:
        metas = _metas_usuario(db, usuario_id)
        registros = db.query(RegistroConsumoDB).filter(
            RegistroConsumoDB.usuario_id == usuario_id,
            RegistroConsumoDB.fecha == fecha,
        ).all()
    finally:
        db.close()

    tot = {
        "calorias": round(sum(r.calorias or 0 for r in registros), 1),
        "proteinas": round(sum(r.proteinas or 0 for r in registros), 1),
        "carbohidratos": round(sum(r.carbohidratos or 0 for r in registros), 1),
        "grasas": round(sum(r.grasas or 0 for r in registros), 1),
    }
    pct_kcal = round(tot["calorias"] / metas["calorias"] * 100, 1) if metas["calorias"] else 0.0
    pct_prot = round(tot["proteinas"] / metas["proteinas"] * 100, 1) if metas["proteinas"] else 0.0
    return {
        "fecha": fecha,
        "num_registros": len(registros),
        **tot,
        "meta_calorias": metas["calorias"],
        "meta_proteinas": metas["proteinas"],
        "meta_carbohidratos": metas["carbohidratos"],
        "meta_grasas": metas["grasas"],
        "cumplimiento_calorias_pct": pct_kcal,
        "cumplimiento_proteinas_pct": pct_prot,
        "meta_cumplida": 90 <= pct_kcal <= 110 and pct_prot >= 100,
    }


def _cabecera(ws, fila: int, titulos: List[str]) -> None:
    for col, titulo in enumerate(titulos, start=1):
        celda = ws.cell(row=fila, column=col, value=titulo)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", start_color=COLOR_CABECERA, end_color=COLOR_CABECERA)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[fila].height = 30


def _titulo(ws, texto: str, subtitulo: str) -> None:
    ws["A1"] = texto
    ws["A1"].font = Font(bold=True, size=16, color=COLOR_TITULO)
    ws["A2"] = subtitulo
    ws["A2"].font = Font(italic=True, size=10, color="5E5E5E")


def _anchos(ws, anchos: List[int]) -> None:
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho


def _tabla(ws, nombre: str, ref: str) -> None:
    tabla = Table(displayName=nombre, ref=ref)
    tabla.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(tabla)


def _hoja_diario(wb: Workbook, registros: List[RegistroConsumoDB], etiqueta_mes: str) -> int:
    ws = wb.active
    ws.title = "Diario"
    _titulo(ws, "Diario de consumo", etiqueta_mes)
    fila_cab = 4
    _cabecera(ws, fila_cab, ["Fecha", "Alimento", "Calorías (kcal)", "Proteínas (g)", "Carbohidratos (g)", "Grasas (g)"])

    fila = fila_cab
    for r in registros:
        fila += 1
        try:
            fecha_celda = date.fromisoformat(r.fecha)
        except (TypeError, ValueError):
            fecha_celda = r.fecha
        ws.cell(row=fila, column=1, value=fecha_celda).number_format = "DD/MM/YYYY"
        ws.cell(row=fila, column=2, value=r.nombre)
        for col, valor in enumerate([r.calorias, r.proteinas, r.carbohidratos, r.grasas], start=3):
            ws.cell(row=fila, column=col, value=round(valor or 0, 1)).number_format = "0.0"

    if fila > fila_cab:
        _tabla(ws, "TablaDiario", f"A{fila_cab}:F{fila}")
        total = fila + 1
        ws.cell(row=total, column=2, value="TOTAL MES").font = Font(bold=True)
        for col in range(3, 7):
            letra = get_column_letter(col)
            c = ws.cell(row=total, column=col, value=f"=SUBTOTAL(109,{letra}{fila_cab + 1}:{letra}{fila})")
            c.font = Font(bold=True)
            c.number_format = "0.0"
    else:
        ws.cell(row=fila_cab + 1, column=1, value="Sin registros este mes.").font = Font(italic=True, color="5E5E5E")

    ws.freeze_panes = f"A{fila_cab + 1}"
    _anchos(ws, [13, 38, 15, 15, 17, 13])
    return fila


def _hoja_despensa(wb: Workbook, items: List[PantryDB]) -> None:
    ws = wb.create_sheet("Despensa")
    _titulo(ws, "Despensa virtual", f"Inventario a {date.today().strftime('%d/%m/%Y')}")
    fila_cab = 4
    _cabecera(ws, fila_cab, [
        "Alimento", "Cantidad (g)", "Fecha de registro",
        "kcal / 100g", "Proteínas / 100g", "Carbohidratos / 100g", "Grasas / 100g",
        "kcal en stock", "Proteínas en stock (g)",
    ])

    fila = fila_cab
    for it in items:
        fila += 1
        ws.cell(row=fila, column=1, value=it.nombre)
        ws.cell(row=fila, column=2, value=round(it.cantidad_gramos or 0, 1)).number_format = "0"
        fecha = getattr(it, "fecha_registro", None)
        try:
            fecha = date.fromisoformat(fecha) if fecha else "—"
        except ValueError:
            pass
        ws.cell(row=fila, column=3, value=fecha).number_format = "DD/MM/YYYY"
        for col, valor in enumerate([it.calorias_100g, it.proteinas_100g, it.carbohidratos_100g, it.grasas_100g], start=4):
            ws.cell(row=fila, column=col, value=round(valor or 0, 1)).number_format = "0.0"
        ws.cell(row=fila, column=8, value=f"=B{fila}*D{fila}/100").number_format = "0"
        ws.cell(row=fila, column=9, value=f"=B{fila}*E{fila}/100").number_format = "0.0"

    if fila > fila_cab:
        _tabla(ws, "TablaDespensa", f"A{fila_cab}:I{fila}")
    else:
        ws.cell(row=fila_cab + 1, column=1, value="La despensa está vacía.").font = Font(italic=True, color="5E5E5E")

    ws.freeze_panes = f"A{fila_cab + 1}"
    _anchos(ws, [32, 13, 16, 12, 15, 18, 13, 14, 20])


def _hoja_kpis(wb: Workbook, anio: int, mes: int, metas: Dict[str, float], ultima_fila_diario: int) -> None:
    ws = wb.create_sheet("KPIs & Gráficos")
    _titulo(ws, "KPIs del mes", "Verde: 90–110% de la meta calórica y proteína ≥ 100%. Ámbar: cerca. Rojo: fuera.")

    # Bloque de metas (referenciado en las fórmulas)
    ws["A4"], ws["B4"] = "Meta calorías", metas["calorias"]
    ws["A5"], ws["B5"] = "Meta proteínas", metas["proteinas"]
    ws["A6"], ws["B6"] = "Meta carbohidratos", metas["carbohidratos"]
    ws["A7"], ws["B7"] = "Meta grasas", metas["grasas"]
    for f in range(4, 8):
        ws.cell(row=f, column=1).font = Font(bold=True)
        ws.cell(row=f, column=2).number_format = "0"

    fila_cab = 10
    _cabecera(ws, fila_cab, [
        "Fecha", "Calorías", "Proteínas", "Carbohidratos", "Grasas",
        "Meta kcal", "% kcal", "% proteína", "¿Meta cumplida?",
    ])

    hoy = date.today()
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    if (anio, mes) == (hoy.year, hoy.month):
        ultimo_dia = hoy.day
    fin_diario = max(ultima_fila_diario, 5)
    rango = lambda letra: f"Diario!${letra}$5:${letra}${fin_diario}"

    primera = fila_cab + 1
    fila = fila_cab
    for dia in range(1, ultimo_dia + 1):
        fila += 1
        ws.cell(row=fila, column=1, value=date(anio, mes, dia)).number_format = "DD/MM"
        for col, letra in zip(range(2, 6), "CDEF"):
            c = ws.cell(row=fila, column=col, value=f"=SUMIFS({rango(letra)},{rango('A')},$A{fila})")
            c.number_format = "0"
        ws.cell(row=fila, column=6, value="=$B$4").number_format = "0"
        ws.cell(row=fila, column=7, value=f'=IF(B{fila}=0,"",B{fila}/$B$4)').number_format = "0%"
        ws.cell(row=fila, column=8, value=f'=IF(B{fila}=0,"",C{fila}/$B$5)').number_format = "0%"
        ws.cell(row=fila, column=9, value=f'=IF(B{fila}=0,"",IF(AND(G{fila}>=0.9,G{fila}<=1.1,H{fila}>=1),"Sí","No"))')
        ws.cell(row=fila, column=9).alignment = Alignment(horizontal="center")
        for col in range(1, 10):
            ws.cell(row=fila, column=col).border = BORDE_FINO
    ultima = fila

    # Formato condicional: semáforo de cumplimiento
    rango_kcal = f"G{primera}:G{ultima}"
    ws.conditional_formatting.add(rango_kcal, FormulaRule(
        formula=[f'AND(G{primera}<>"",G{primera}>=0.9,G{primera}<=1.1)'], fill=FILL_OK, font=FONT_OK))
    ws.conditional_formatting.add(rango_kcal, FormulaRule(
        formula=[f'AND(G{primera}<>"",G{primera}>=0.8,G{primera}<=1.2)'], fill=FILL_AVISO, font=FONT_AVISO))
    ws.conditional_formatting.add(rango_kcal, FormulaRule(
        formula=[f'G{primera}<>""'], fill=FILL_MAL, font=FONT_MAL))

    rango_prot = f"H{primera}:H{ultima}"
    ws.conditional_formatting.add(rango_prot, FormulaRule(
        formula=[f'AND(H{primera}<>"",H{primera}>=1)'], fill=FILL_OK, font=FONT_OK))
    ws.conditional_formatting.add(rango_prot, FormulaRule(
        formula=[f'AND(H{primera}<>"",H{primera}>=0.85)'], fill=FILL_AVISO, font=FONT_AVISO))
    ws.conditional_formatting.add(rango_prot, FormulaRule(
        formula=[f'H{primera}<>""'], fill=FILL_MAL, font=FONT_MAL))

    rango_ok = f"I{primera}:I{ultima}"
    ws.conditional_formatting.add(rango_ok, CellIsRule(operator="equal", formula=['"Sí"'], fill=FILL_OK, font=FONT_OK))
    ws.conditional_formatting.add(rango_ok, CellIsRule(operator="equal", formula=['"No"'], fill=FILL_MAL, font=FONT_MAL))

    # Resumen con promedios automáticos (solo días con registros)
    ws["D4"], ws["E4"] = "Promedio kcal / día", f'=IFERROR(AVERAGEIF(B{primera}:B{ultima},">0"),0)'
    ws["D5"], ws["E5"] = "Promedio proteínas / día", f'=IFERROR(AVERAGEIF(C{primera}:C{ultima},">0"),0)'
    ws["D6"], ws["E6"] = "Días registrados", f'=COUNTIF(B{primera}:B{ultima},">0")'
    ws["D7"], ws["E7"] = "Días con meta cumplida", f'=COUNTIF(I{primera}:I{ultima},"Sí")'
    ws["D8"], ws["E8"] = "% de constancia", f'=IFERROR(E7/E6,0)'
    for f in range(4, 9):
        ws.cell(row=f, column=4).font = Font(bold=True)
        ws.cell(row=f, column=5).number_format = "0"
    ws["E8"].number_format = "0%"
    ws.conditional_formatting.add("E8", CellIsRule(operator="greaterThanOrEqual", formula=["0.8"], fill=FILL_OK, font=FONT_OK))
    ws.conditional_formatting.add("E8", CellIsRule(operator="between", formula=["0.5", "0.7999"], fill=FILL_AVISO, font=FONT_AVISO))
    ws.conditional_formatting.add("E8", CellIsRule(operator="lessThan", formula=["0.5"], fill=FILL_MAL, font=FONT_MAL))

    ws.freeze_panes = f"B{primera}"
    _anchos(ws, [20, 11, 11, 24, 11, 11, 9, 11, 15])

    # Gráficos nativos de Excel
    fechas = Reference(ws, min_col=1, min_row=primera, max_row=ultima)

    linea = LineChart()
    linea.title = "Calorías diarias vs meta"
    linea.y_axis.title = "kcal"
    linea.height, linea.width = 8, 18
    linea.add_data(Reference(ws, min_col=2, min_row=fila_cab, max_row=ultima), titles_from_data=True)
    linea.add_data(Reference(ws, min_col=6, min_row=fila_cab, max_row=ultima), titles_from_data=True)
    linea.set_categories(fechas)
    linea.series[0].graphicalProperties.line.solidFill = "4981D4"
    linea.series[0].graphicalProperties.line.width = 28000
    linea.series[1].graphicalProperties.line.solidFill = "49C6D4"
    linea.series[1].graphicalProperties.line.dashStyle = "dash"
    for serie in linea.series:
        serie.smooth = False
    ws.add_chart(linea, "K4")

    barras = BarChart()
    barras.type = "col"
    barras.grouping = "stacked"
    barras.overlap = 100
    barras.title = "Macros diarios (g)"
    barras.y_axis.title = "gramos"
    barras.height, barras.width = 8, 18
    barras.add_data(Reference(ws, min_col=3, max_col=5, min_row=fila_cab, max_row=ultima), titles_from_data=True)
    barras.set_categories(fechas)
    for serie, color in zip(barras.series, ["5749D4", "49C6D4", "4981D4"]):
        serie.graphicalProperties.solidFill = color
        serie.graphicalProperties.line.solidFill = color
    ws.add_chart(barras, "K22")


def generar_reporte_mensual(usuario_id: int, anio: int, mes: int) -> bytes:
    """Genera el .xlsx del mes indicado para un usuario y devuelve sus bytes."""
    if not 1 <= mes <= 12:
        raise ValueError("El mes debe estar entre 1 y 12.")
    inicio = date(anio, mes, 1).isoformat()
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1]).isoformat()

    db = SessionLocal()
    try:
        registros = db.query(RegistroConsumoDB).filter(
            RegistroConsumoDB.usuario_id == usuario_id,
            RegistroConsumoDB.fecha >= inicio,
            RegistroConsumoDB.fecha <= fin,
        ).order_by(RegistroConsumoDB.fecha, RegistroConsumoDB.id).all()
        despensa = db.query(PantryDB).filter(PantryDB.usuario_id == usuario_id).order_by(PantryDB.nombre).all()
        metas = _metas_usuario(db, usuario_id)
    finally:
        db.close()

    etiqueta_mes = f"{MESES[mes - 1]} {anio}"
    wb = Workbook()
    ultima_fila_diario = _hoja_diario(wb, registros, f"Reporte mensual {etiqueta_mes}")
    _hoja_despensa(wb, despensa)
    _hoja_kpis(wb, anio, mes, metas, ultima_fila_diario)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
