import json
import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.models.chat import MensajeChat, RespuestaChat, SolicitudChat
from app.models.daily import RegistroConsumo
from app.services import daily_service

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
        "explicacion": f"Para aportar ~{proteinas_objetivo}g prot o ~{carbohidratos_objetivo}g carbs con {alimento}, necesitas exactamente {gramos_recomendados}g."
    }, ensure_ascii=False)


def herramienta_registrar_comida_consumida(
    nombre: str,
    calorias: float,
    proteinas: float,
    carbohidratos: float,
    grasas: float,
    usuario_id: int
) -> str:
    registro = RegistroConsumo(
        nombre=nombre,
        calorias=float(calorias),
        proteinas=float(proteinas),
        carbohidratos=float(carbohidratos),
        grasas=float(grasas)
    )
    daily_service.registrar_consumo(registro, usuario_id)
    resumen = daily_service.obtener_resumen_diario(usuario_id)

    return json.dumps({
        "status": "exito",
        "mensaje": f"Registrado '{nombre}' en tu diario (+{calorias} kcal, +{proteinas}g prot, +{carbohidratos}g carbs, +{grasas}g grasas).",
        "calorias_restantes": resumen.calorias_restantes,
        "proteinas_restantes": resumen.proteinas_restantes
    }, ensure_ascii=False)


HERRAMIENTAS_DEFINICION = [
    {
        "type": "function",
        "function": {
            "name": "herramienta_calcular_porcion_exacta",
            "description": "Calcula en gramos la ración exacta de un alimento para llegar a una meta de macros.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "herramienta_registrar_comida_consumida",
            "description": "Registra una comida consumida en el diario sumando sus macros. USAR ÚNICAMENTE cuando el usuario confirme explícitamente haber comido algo (ej: 'He comido 200g de pollo', 'Añade 3 huevos'). NUNCA usar al sugerir o recomendar recetas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre de la comida consumida"},
                    "calorias": {"type": "number", "description": "Calorías consumidas"},
                    "proteinas": {"type": "number", "description": "Proteínas consumidas en g"},
                    "carbohidratos": {"type": "number", "description": "Carbohidratos consumidos en g"},
                    "grasas": {"type": "number", "description": "Grasas consumidas en g"}
                },
                "required": ["nombre", "calorias", "proteinas", "carbohidratos", "grasas"]
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

    reserva = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen/qwen3.8-27b"]
    for m in reserva:
        if m not in modelos_encontrados:
            modelos_encontrados.append(m)

    return modelos_encontrados


async def procesar_chat_agente(solicitud: SolicitudChat, usuario_id: int) -> RespuestaChat:
    if not settings.GROQ_API_KEY:
        return RespuestaChat(
            respuesta="Configura GROQ_API_KEY en tu archivo .env para interactuar con el agente.",
            herramientas_usadas=[]
        )

    resumen_diario = daily_service.obtener_resumen_diario(usuario_id)

    prompt_sistema = (
        "Eres NutriAI Agent, un asistente experto e ingenioso en ingeniería nutricional y dietética.\n"
        f"ESTADO DE DIARIO DEL USUARIO HOY:\n"
        f"- Consumido: {resumen_diario.calorias_totales} kcal / Meta: {resumen_diario.objetivos.calorias_objetivo} kcal (Faltan: {resumen_diario.calorias_restantes} kcal)\n"
        f"- Proteínas: {resumen_diario.proteinas_totales}g / Meta: {resumen_diario.objetivos.proteinas_objetivo}g (Faltan: {resumen_diario.proteinas_restantes}g)\n"
        f"- Carbohidratos: {resumen_diario.carbohidratos_totales}g / Meta: {resumen_diario.objetivos.carbohidratos_objetivo}g (Faltan: {resumen_diario.carbohidratos_restantes}g)\n"
        f"- Grasas: {resumen_diario.grasas_totales}g / Meta: {resumen_diario.objetivos.grasas_objetivo}g (Faltan: {resumen_diario.grasas_restantes}g)\n\n"
        "REGLAS CRÍTICAS DE HERRAMIENTAS:\n"
        "1. 'herramienta_calcular_porcion_exacta': Usa esta herramienta para calcular la ración matemática exacta si el usuario te lo solicita.\n"
        "2. 'herramienta_registrar_comida_consumida': Usa esta herramienta ÚNICAMENTE cuando el usuario te diga explícitamente que HA COMIDO o QUIERE ANOTAR/REGISTRAR algo (ej: 'He comido 200g de pollo', 'Añade mi almuerzo').\n"
        "3. PROHIBICIÓN: NUNCA ejecutes 'herramienta_registrar_comida_consumida' si solo estás sugiriendo o recomendando recetas futuras."
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

                        resultado_tool = ""
                        if fn_name == "herramienta_calcular_porcion_exacta":
                            herramientas_ejecutadas.append(fn_name)
                            resultado_tool = herramienta_calcular_porcion_exacta(**fn_args)
                        elif fn_name == "herramienta_registrar_comida_consumida":
                            herramientas_ejecutadas.append(fn_name)
                            # El usuario siempre es el autenticado, nunca el que proponga el modelo
                            fn_args.pop("usuario_id", None)
                            resultado_tool = herramienta_registrar_comida_consumida(**fn_args, usuario_id=usuario_id)

                        if resultado_tool:
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
            respuesta=f"Error conectando con los modelos de Groq. Detalle: {', '.join(errores_acumulados[:2])}",
            herramientas_usadas=[]
        )