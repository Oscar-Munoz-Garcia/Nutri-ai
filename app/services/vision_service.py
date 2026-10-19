import base64
import json
import httpx
from app.core.config import settings
from app.models.food import ProductoNutricional

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


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

    # Lista de modelos de visión compatibles en Groq (probaremos el primero activo)
    modelos_vision = [
        "llama-3.2-11b-vision-instruct",
        "llama-3.2-90b-vision-instruct",
        "qwen/qwen3.8-27b"
    ]

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        ultimo_error = ""
        for modelo in modelos_vision:
            payload = {
                "model": modelo,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_instrucciones},
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
                "max_tokens": 500,
                "response_format": {"type": "json_object"}
            }

            try:
                response = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
                if response.status_code == 200:
                    res_data = response.json()
                    contenido = res_data["choices"][0]["message"]["content"].strip()
                    
                    if "```" in contenido:
                        lineas = [l for l in contenido.split("\n") if not l.strip().startswith("```")]
                        contenido = "\n".join(lineas).strip()

                    datos_nutri = json.loads(contenido)

                    return ProductoNutricional(
                        codigo_barras="GROQ_" + str(abs(hash(imagen_b64[:30])))[:8],
                        nombre=str(datos_nutri.get("nombre", "Producto Detectado")),
                        marca=str(datos_nutri.get("marca", "Desconocida")),
                        calorias_100g=float(datos_nutri.get("calorias_100g", 0.0)),
                        proteinas_100g=float(datos_nutri.get("proteinas_100g", 0.0)),
                        carbohidratos_100g=float(datos_nutri.get("carbohidratos_100g", 0.0)),
                        grasas_100g=float(datos_nutri.get("grasas_100g", 0.0))
                    )
                else:
                    ultimo_error = f"HTTP {response.status_code}: {response.text}"
            except Exception as e:
                ultimo_error = str(e)

        return ProductoNutricional(
            codigo_barras="GROQ_ERROR",
            nombre=f"Error API Groq ({ultimo_error[:60]})",
            marca="Error",
            calorias_100g=0.0,
            proteinas_100g=0.0,
            carbohidratos_100g=0.0,
            grasas_100g=0.0
        )