import base64
import json
import mimetypes
import httpx
from typing import Optional
from app.core.config import settings
from app.models.food import ProductoNutricional
from app.models.vision import ProductoOCR

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
