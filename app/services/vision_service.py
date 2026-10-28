import base64
import json
import mimetypes
import httpx
from typing import Optional
from app.core.config import settings
from app.models.food import ProductoNutricional
from app.models.vision import ProductoOCR, AnalisisPlato, IngredientePlato

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# Lista de modelos de visión compatibles en Groq (probaremos el primero activo)
MODELOS_VISION = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.2-11b-vision-instruct",
    "llama-3.2-90b-vision-instruct",
    "qwen/qwen3.8-27b"
]


def _content_type_desde_nombre(nombre_archivo: str) -> str:
    tipo, _ = mimetypes.guess_type(nombre_archivo or "")
    return tipo if tipo and tipo.startswith("image/") else "image/jpeg"


def _limpiar_json(contenido: str) -> dict:
    contenido = contenido.strip()
    if "```" in contenido:
        lineas = [l for l in contenido.split("\n") if not l.strip().startswith("```")]
        contenido = "\n".join(lineas).strip()
    return json.loads(contenido)


def _num(valor, defecto: float = 0.0) -> float:
    try:
        return round(float(valor), 1)
    except (TypeError, ValueError):
        return defecto


async def _consultar_groq_vision(prompt: str, imagen_b64: str, content_type: str, max_tokens: int = 500) -> tuple[Optional[dict], str]:
    """
    Envía la imagen y el prompt a Groq Vision probando los modelos en orden.
    Devuelve (json_respuesta, ultimo_error). json_respuesta es None si todos fallan.
    """
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    ultimo_error = ""
    async with httpx.AsyncClient(timeout=25.0) as client:
        for modelo in MODELOS_VISION:
            payload = {
                "model": modelo,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{imagen_b64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}
            }

            try:
                response = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
                if response.status_code == 200:
                    res_data = response.json()
                    return _limpiar_json(res_data["choices"][0]["message"]["content"]), ""
                ultimo_error = f"HTTP {response.status_code}: {response.text}"
            except Exception as e:
                ultimo_error = str(e)

    return None, ultimo_error


async def analizar_etiqueta_imagen(
    contenido_imagen: bytes,
    content_type: str = "image/jpeg"
) -> ProductoNutricional:
    """
    Recibe los bytes de una imagen de etiqueta nutricional, la codifica en Base64
    y consulta a la API de Visión de Groq para extraer los macronutrientes.
    """
    # 1. Convertir los bytes de la imagen a Base64
    imagen_b64 = base64.b64encode(contenido_imagen).decode("utf-8")

    # 2. Si no hay GROQ_API_KEY configurada, devolvemos la respuesta de prueba (Mock)
    if not settings.GROQ_API_KEY:
        return ProductoNutricional(
            codigo_barras="OCR_MOCK_001",
            nombre="Producto extraído por OCR (Modo Prueba Sin Groq)",
            marca="Marca Simulada",
            calorias_100g=210.0,
            proteinas_100g=18.5,
            carbohidratos_100g=12.0,
            grasas_100g=9.5,
            imagen_url=None
        )

    prompt_instrucciones = (
        "Eres un experto en nutrición y OCR. Analiza la imagen suministrada de una tabla o etiqueta nutricional.\n"
        "Extrae los valores nutricionales referidos a 100 gramos o 100 mililitros.\n"
        "Debes responder ÚNICAMENTE con un objeto JSON válido con este formato exacto:\n"
        "{\n"
        '  "nombre": "Nombre del producto o tipo de alimento",\n'
        '  "marca": "Marca del producto o Desconocida",\n'
        '  "calorias_100g": 0.0,\n'
        '  "proteinas_100g": 0.0,\n'
        '  "carbohidratos_100g": 0.0,\n'
        '  "grasas_100g": 0.0\n'
        "}\n"
        "No incluyas explicaciones ni marcas de formato markdown fuera del objeto JSON."
    )

    datos_nutri, ultimo_error = await _consultar_groq_vision(prompt_instrucciones, imagen_b64, content_type)

    if datos_nutri is None:
        return ProductoNutricional(
            codigo_barras="GROQ_ERROR",
            nombre=f"Error API Groq ({ultimo_error[:60]})",
            marca="Error",
            calorias_100g=0.0,
            proteinas_100g=0.0,
            carbohidratos_100g=0.0,
            grasas_100g=0.0
        )

    return ProductoNutricional(
        codigo_barras="GROQ_" + str(abs(hash(imagen_b64[:30])))[:8],
        nombre=str(datos_nutri.get("nombre", "Producto Detectado")),
        marca=str(datos_nutri.get("marca", "Desconocida")),
        calorias_100g=_num(datos_nutri.get("calorias_100g")),
        proteinas_100g=_num(datos_nutri.get("proteinas_100g")),
        carbohidratos_100g=_num(datos_nutri.get("carbohidratos_100g")),
        grasas_100g=_num(datos_nutri.get("grasas_100g"))
    )


async def analizar_etiqueta_nutricional(contenido_imagen: bytes, nombre_archivo: str = "etiqueta.jpg") -> ProductoOCR:
    """Adaptador usado por el endpoint /alimentos/vision-ocr."""
    producto = await analizar_etiqueta_imagen(contenido_imagen, _content_type_desde_nombre(nombre_archivo))
    return ProductoOCR(
        nombre=producto.nombre,
        calorias_100g=producto.calorias_100g,
        proteinas_100g=producto.proteinas_100g,
        carbohidratos_100g=producto.carbohidratos_100g,
        grasas_100g=producto.grasas_100g,
        confianza=0.0 if producto.codigo_barras == "GROQ_ERROR" else 1.0
    )


def _construir_analisis(nombre_plato: str, ingredientes: list, confianza: float, notas: str, modo_prueba: bool = False) -> AnalisisPlato:
    """Recalcula los totales a partir de los ingredientes para que siempre cuadren."""
    return AnalisisPlato(
        nombre_plato=nombre_plato,
        ingredientes=ingredientes,
        peso_total_g=round(sum(i.peso_estimado_g for i in ingredientes), 1),
        calorias_totales=round(sum(i.calorias for i in ingredientes), 1),
        proteinas_totales=round(sum(i.proteinas for i in ingredientes), 1),
        carbohidratos_totales=round(sum(i.carbohidratos for i in ingredientes), 1),
        grasas_totales=round(sum(i.grasas for i in ingredientes), 1),
        confianza=max(0.0, min(1.0, confianza)),
        notas=notas,
        modo_prueba=modo_prueba
    )


async def analizar_plato(contenido_imagen: bytes, nombre_archivo: str = "plato.jpg", idioma: str = "es") -> AnalisisPlato:
    """
    Analiza la foto de un plato preparado con Groq Vision y estima los ingredientes,
    el peso de cada uno y sus macros aproximados. Los nombres y las notas salen en el idioma pedido ('es' o 'en').
    """
    lengua = "inglés" if idioma == "en" else "español"
    if not settings.GROQ_API_KEY:
        ingredientes = [
            IngredientePlato(nombre="Arroz blanco cocido", peso_estimado_g=150, calorias=195, proteinas=4.1, carbohidratos=42.0, grasas=0.4),
            IngredientePlato(nombre="Pechuga de pollo a la plancha", peso_estimado_g=120, calorias=198, proteinas=37.2, carbohidratos=0.0, grasas=4.3),
            IngredientePlato(nombre="Aguacate", peso_estimado_g=50, calorias=80, proteinas=1.0, carbohidratos=4.3, grasas=7.3)
        ]
        return _construir_analisis(
            "Arroz con pollo y aguacate (Modo Prueba Sin Groq)",
            ingredientes,
            0.5,
            "Estimación simulada: configura GROQ_API_KEY para analizar la foto real.",
            modo_prueba=True
        )

    imagen_b64 = base64.b64encode(contenido_imagen).decode("utf-8")
    prompt = (
        "Eres un nutricionista experto en estimar raciones a partir de fotos.\n"
        "Analiza la foto de este plato de comida real. Identifica cada ingrediente visible, "
        "estima su peso en gramos (usa el tamaño del plato y los cubiertos como referencia) y calcula "
        "las calorías y macros de esa cantidad (no por 100g). Ten en cuenta aceites y salsas visibles.\n"
        "Responde ÚNICAMENTE con un objeto JSON válido con este formato exacto:\n"
        "{\n"
        f'  "nombre_plato": "Nombre corto del plato en {lengua}",\n'
        '  "ingredientes": [\n'
        '    {"nombre": "Ingrediente", "peso_estimado_g": 0.0, "calorias": 0.0, "proteinas": 0.0, "carbohidratos": 0.0, "grasas": 0.0}\n'
        "  ],\n"
        '  "confianza": 0.0,\n'
        '  "notas": "Supuestos de la estimación en una frase"\n'
        "}\n"
        f"Escribe los nombres de los ingredientes y las notas en {lengua}.\n"
        "confianza va de 0 a 1. Si la imagen no muestra comida, devuelve ingredientes vacío y explícalo en notas.\n"
        "No incluyas explicaciones ni marcas de formato markdown fuera del objeto JSON."
    )

    datos, ultimo_error = await _consultar_groq_vision(prompt, imagen_b64, _content_type_desde_nombre(nombre_archivo), max_tokens=900)

    if datos is None:
        return _construir_analisis("No se pudo analizar el plato", [], 0.0, f"Error API Groq ({ultimo_error[:80]})")

    ingredientes = []
    for ing in datos.get("ingredientes") or []:
        if not isinstance(ing, dict) or not ing.get("nombre"):
            continue
        ingredientes.append(IngredientePlato(
            nombre=str(ing["nombre"]),
            peso_estimado_g=_num(ing.get("peso_estimado_g")),
            calorias=_num(ing.get("calorias")),
            proteinas=_num(ing.get("proteinas")),
            carbohidratos=_num(ing.get("carbohidratos")),
            grasas=_num(ing.get("grasas"))
        ))

    return _construir_analisis(
        str(datos.get("nombre_plato") or "Plato detectado"),
        ingredientes,
        _num(datos.get("confianza"), 0.5),
        str(datos.get("notas") or "")
    )
