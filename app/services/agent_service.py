import json
import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.models.chat import MensajeChat, RespuestaChat, SolicitudChat

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_ENDPOINT = "https://api.groq.com/openai/v1/models"


def herramienta_calcular_porcion_exacta(
    alimento: str,
    proteinas_objetivo: float,
    carbohidratos_objetivo: float,
    proteinas_100g: float,
    carbohidratos_100g: float
) -> str:
    gramos_por_prot = (proteinas_objetivo / proteinas_100g * 100) if proteinas_100g > 0 else 0
    gramos_por_carb = (carbohidratos_objetivo / carbohidratos_100g * 100) if carbohidratos_100g > 0 else 0
    
    gramos_recomendados = round(max(gramos_por_prot, gramos_por_carb), 1)
    
    return json.dumps({
        "alimento": alimento,
        "gramos_recomendados": gramos_recomendados,
        "explicacion": f"Para aportar ~{proteinas_objetivo}g de proteína o ~{carbohidratos_objetivo}g de carbs con {alimento}, necesitas exactamente {gramos_recomendados}g."
    })


HERRAMIENTAS_DEFINICION = [
    {
        "type": "function",
        "function": {
            "name": "herramienta_calcular_porcion_exacta",
            "description": "Calcula matemáticamente en gramos la ración exacta de un alimento para llegar a una meta de proteínas o carbohidratos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "alimento": {"type": "string", "description": "Nombre del alimento"},
                    "proteinas_objetivo": {"type": "number", "description": "Gramos de proteína requeridos"},
                    "carbohidratos_objetivo": {"type": "number", "description": "Gramos de carbohidratos requeridos"},
                    "proteinas_100g": {"type": "number", "description": "Proteínas por 100g del alimento"},
                    "carbohidratos_100g": {"type": "number", "description": "Carbohidratos por 100g del alimento"}
                },
                "required": ["alimento", "proteinas_objetivo", "carbohidratos_objetivo", "proteinas_100g", "carbohidratos_100g"]
            }
        }
    }
]


async def obtener_modelos_disponibles(client: httpx.AsyncClient, headers: dict) -> List[str]:
    modelos_encontrados = []
    try:
        res = await client.get(GROQ_MODELS_ENDPOINT, headers=headers)
        if res.status_code == 200:
            datos = res.json().get("data", [])
            for item in datos:
                model_id = item.get("id", "")
                if not any(x in model_id.lower() for x in ["whisper", "guard", "audio", "safeguard", "orpheus"]):
                    modelos_encontrados.append(model_id)
    except Exception:
        pass

    reserva = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3.8-27b",
        "gemma2-9b-it"
    ]
    for m in reserva:
        if m not in modelos_encontrados:
            modelos_encontrados.append(m)

    return modelos_encontrados


async def procesar_chat_agente(solicitud: SolicitudChat) -> RespuestaChat:
    if not settings.GROQ_API_KEY:
        return RespuestaChat(
            respuesta="El agente de chat requiere configurar la clave GROQ_API_KEY en el archivo .env.",
            herramientas_usadas=[]
        )

    prompt_sistema = (
        "Eres NutriAI Agent, un asistente experto en ingeniería nutricional y dietética.\n"
        "Tu objetivo es ayudar al usuario a ajustar sus comidas según sus macros diarios.\n"
        "Cuando el usuario te pida calcular cantidades de alimentos para alcanzar sus macros, "
        "SIEMPRE utiliza la herramienta 'herramienta_calcular_porcion_exacta' para realizar el cálculo matemático real.\n"
        "Sé preciso, conciso y profesional."
    )

    mensajes = [{"role": "system", "content": prompt_sistema}]
    for m in solicitud.historial:
        mensajes.append({"role": m.role, "content": m.content})

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    herramientas_ejecutadas = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        modelos_candidatos = await obtener_modelos_disponibles(client, headers)
        errores_acumulados = []

        for modelo in modelos_candidatos:
            payload = {
                "model": modelo,
                "messages": mensajes,
                "tools": HERRAMIENTAS_DEFINICION,
                "tool_choice": "auto",
                "temperature": 0.2
            }

            try:
                res = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
                if res.status_code == 200:
                    res_data = res.json()
                    mensaje_respuesta = res_data["choices"][0]["message"]

                    if "tool_calls" in mensaje_respuesta and mensaje_respuesta["tool_calls"]:
                        tool_call = mensaje_respuesta["tool_calls"][0]
                        fn_name = tool_call["function"]["name"]
                        fn_args = json.loads(tool_call["function"]["arguments"])

                        if fn_name == "herramienta_calcular_porcion_exacta":
                            herramientas_ejecutadas.append(fn_name)
                            resultado_tool = herramienta_calcular_porcion_exacta(**fn_args)

                            mensajes.append(mensaje_respuesta)
                            mensajes.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": resultado_tool
                            })

                            payload_final = {
                                "model": modelo,
                                "messages": mensajes,
                                "temperature": 0.2
                            }

                            res_final = await client.post(GROQ_ENDPOINT, headers=headers, json=payload_final)
                            if res_final.status_code == 200:
                                contenido_final = res_final.json()["choices"][0]["message"]["content"]
                                return RespuestaChat(
                                    respuesta=contenido_final,
                                    herramientas_usadas=herramientas_ejecutadas
                                )

                    return RespuestaChat(
                        respuesta=mensaje_respuesta.get("content", "Sin respuesta"),
                        herramientas_usadas=herramientas_ejecutadas
                    )
                else:
                    errores_acumulados.append(f"{modelo} (HTTP {res.status_code})")
            except Exception as e:
                errores_acumulados.append(f"{modelo} ({str(e)})")

        return RespuestaChat(
            respuesta=f"No se pudo conectar con ningún modelo de Groq activo. Detalle: {', '.join(errores_acumulados[:3])}",
            herramientas_usadas=[]
        )