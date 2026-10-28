"""Sincronización del resumen diario con Google Sheets mediante un webhook de Apps Script."""
import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import httpx

from app.db.session import SessionLocal
from app.db.models import UsuarioDB
from app.services.export_service import resumen_dia

logger = logging.getLogger("nutri_ai.sheets")


def _config() -> Dict[str, Optional[str]]:
    return {
        "url": os.getenv("GOOGLE_SHEETS_WEBHOOK_URL") or None,
        "secreto": os.getenv("GOOGLE_SHEETS_WEBHOOK_SECRET") or None,
        "hora_cierre": os.getenv("GOOGLE_SHEETS_HORA_CIERRE") or None,  # "HH:MM", hora local
    }


def estado() -> Dict:
    cfg = _config()
    return {"configurado": bool(cfg["url"]), "hora_cierre_automatico": cfg["hora_cierre"] if cfg["url"] else None}


class SheetsNoConfigurado(RuntimeError):
    pass


async def enviar_resumen(usuario: UsuarioDB, fecha: Optional[str] = None) -> Dict:
    """Envía (o actualiza) la fila del día del usuario en la hoja compartida."""
    cfg = _config()
    if not cfg["url"]:
        raise SheetsNoConfigurado("Falta GOOGLE_SHEETS_WEBHOOK_URL en el .env.")

    resumen = resumen_dia(usuario.id, fecha)
    payload = {"secreto": cfg["secreto"] or "", "usuario": usuario.username, **resumen}
    # Apps Script responde con una redirección 302 hacia el resultado
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        res = await client.post(cfg["url"], json=payload)
    if res.status_code >= 400:
        raise RuntimeError(f"Google Sheets respondió {res.status_code}.")
    try:
        respuesta = res.json()
    except ValueError:
        respuesta = {}
    if respuesta.get("ok") is False:
        raise RuntimeError(respuesta.get("error") or "Google Sheets rechazó el envío.")
    return {"status": "ok", "enviado": resumen, "hoja": respuesta}


def _segundos_hasta(hora_cierre: str) -> float:
    hh, mm = (int(x) for x in hora_cierre.split(":"))
    ahora = datetime.now()
    objetivo = ahora.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if objetivo <= ahora:
        objetivo += timedelta(days=1)
    return (objetivo - ahora).total_seconds()


async def bucle_cierre_automatico() -> None:
    """Cada día a GOOGLE_SHEETS_HORA_CIERRE envía el resumen de todos los usuarios."""
    hora = _config()["hora_cierre"]
    while True:
        await asyncio.sleep(_segundos_hasta(hora))
        fecha = date.today().isoformat()
        db = SessionLocal()
        try:
            usuarios = db.query(UsuarioDB).all()
        finally:
            db.close()
        for usuario in usuarios:
            try:
                await enviar_resumen(usuario, fecha)
            except Exception as exc:  # un fallo de red no debe parar el bucle
                logger.warning("No se pudo sincronizar %s con Sheets: %s", usuario.username, exc)
        await asyncio.sleep(61)


def iniciar_cierre_automatico() -> Optional[asyncio.Task]:
    cfg = _config()
    if not (cfg["url"] and cfg["hora_cierre"]):
        return None
    try:
        _segundos_hasta(cfg["hora_cierre"])
    except ValueError:
        logger.warning("GOOGLE_SHEETS_HORA_CIERRE debe tener formato HH:MM.")
        return None
    return asyncio.create_task(bucle_cierre_automatico())
