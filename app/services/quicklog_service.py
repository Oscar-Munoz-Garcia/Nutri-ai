import json
import re
import unicodedata
from typing import List, Optional, Tuple
import httpx
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models import PantryDB
from app.models.quicklog import ItemInterpretado, RespuestaRegistroRapido

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODELOS_TEXTO = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

COMIDAS = {
    "desayuno": "Desayuno", "almuerzo": "Almuerzo", "comida": "Comida",
    "merienda": "Merienda", "cena": "Cena", "snack": "Snack", "postre": "Postre",
    # Con la interfaz en inglés
    "breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "dessert": "Dessert"
}

_PATRON_CANTIDAD = re.compile(r"^(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unidad>kg|g|gr|gramos?)\b\s*(?:de\s+|of\s+)?(?P<nombre>.+)$")


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").strip()


def separar_comida(texto: str) -> Tuple[Optional[str], str]:
    """'Desayuno: 3 huevos' -> ('Desayuno', '3 huevos')."""
    limpio = texto.strip()
    m = re.match(r"^\s*([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s*[:,\-]?\s+(.*)$", limpio)
    if m and _normalizar(m.group(1)) in COMIDAS:
        return COMIDAS[_normalizar(m.group(1))], m.group(2).strip()
    return None, limpio


def separar_alimentos(texto: str) -> List[str]:
    partes = re.split(r",|\+|;|\s+y\s+|\s+and\s+|\s+e\s+(?=[hi])", texto, flags=re.IGNORECASE)
    return [p.strip(" .") for p in partes if p and p.strip(" .")]


def _buscar_en_despensa(segmento: str, despensa: List[PantryDB]) -> Optional[ItemInterpretado]:
    """Solo resuelve cantidades en gramos ('80g de avena') contra alimentos de la despensa."""
    m = _PATRON_CANTIDAD.match(_normalizar(segmento))
    if not m:
        return None
    gramos = float(m.group("num").replace(",", "."))
    if m.group("unidad") == "kg":
        gramos *= 1000
    nombre_buscado = m.group("nombre").strip()

    for item in despensa:
        nombre_item = _normalizar(item.nombre or "")
        if nombre_item and (nombre_buscado in nombre_item or nombre_item in nombre_buscado):
            f = gramos / 100.0
            return ItemInterpretado(
                nombre=f"{item.nombre} ({gramos:g}g)",
                calorias=round((item.calorias_100g or 0) * f, 1),
                proteinas=round((item.proteinas_100g or 0) * f, 1),
                carbohidratos=round((item.carbohidratos_100g or 0) * f, 1),
                grasas=round((item.grasas_100g or 0) * f, 1),
                origen="despensa"
            )
    return None


async def _estimar_con_groq(segmentos: List[str]) -> List[ItemInterpretado]:
    prompt = (
        "Eres un nutricionista. Estima los macros de cada alimento de la lista usando valores medios de "
        "tablas nutricionales españolas. Si no se indica cantidad, asume una ración estándar. "
        "Responde SOLO con JSON: {\"items\": [{\"nombre\": str (con la cantidad), \"calorias\": number, "
        "\"proteinas\": number, \"carbohidratos\": number, \"grasas\": number}]}, un objeto por alimento y en el mismo orden."
    )
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        for modelo in MODELOS_TEXTO:
            payload = {
                "model": modelo,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(segmentos, ensure_ascii=False)}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            try:
                res = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
                if res.status_code != 200:
                    continue
                contenido = res.json()["choices"][0]["message"]["content"]
                items = json.loads(contenido).get("items", [])
                return [
                    ItemInterpretado(
                        nombre=str(i.get("nombre", "Alimento")),
                        calorias=round(float(i.get("calorias", 0) or 0), 1),
                        proteinas=round(float(i.get("proteinas", 0) or 0), 1),
                        carbohidratos=round(float(i.get("carbohidratos", 0) or 0), 1),
                        grasas=round(float(i.get("grasas", 0) or 0), 1),
                        origen="ia"
                    ) for i in items
                ]
            except Exception:
                continue
    return []


async def interpretar_texto(texto: str, usuario_id: int) -> RespuestaRegistroRapido:
    """Convierte una frase en entradas del diario sin guardarlas: el usuario las revisa antes."""
    comida, resto = separar_comida(texto)
    segmentos = separar_alimentos(resto)
    avisos: List[str] = []

    db = SessionLocal()
    try:
        despensa = db.query(PantryDB).filter(PantryDB.usuario_id == usuario_id).all()
    finally:
        db.close()

    resueltos: List[Optional[ItemInterpretado]] = [_buscar_en_despensa(s, despensa) for s in segmentos]
    pendientes = [s for s, r in zip(segmentos, resueltos) if r is None]

    estimados: List[ItemInterpretado] = []
    if pendientes:
        if settings.GROQ_API_KEY:
            estimados = await _estimar_con_groq(pendientes)
            if not estimados:
                avisos.append("No se pudo contactar con Groq; revisa los valores antes de guardar.")
        else:
            avisos.append("Sin GROQ_API_KEY solo se calculan alimentos de tu despensa indicados en gramos.")

    items: List[ItemInterpretado] = []
    for segmento, resuelto in zip(segmentos, resueltos):
        if resuelto:
            items.append(resuelto)
        elif estimados:
            items.append(estimados.pop(0))
        else:
            items.append(ItemInterpretado(nombre=segmento, calorias=0, proteinas=0, carbohidratos=0, grasas=0, origen="sin_estimar"))

    if comida:
        for it in items:
            it.nombre = f"{comida} · {it.nombre}"

    return RespuestaRegistroRapido(comida=comida, items=items, avisos=avisos)
