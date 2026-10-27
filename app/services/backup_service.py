import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from app.db.session import engine

logger = logging.getLogger("nutri_ai.backup")

PREFIJO = "nutri_ai_"
FORMATO_FECHA = "%Y%m%d_%H%M%S"
SEGUNDOS_DIA = 24 * 60 * 60


def ruta_bd() -> Path:
    """Ruta del fichero SQLite que usa la app (según DATABASE_URL)."""
    if engine.url.get_backend_name() != "sqlite" or not engine.url.database:
        raise RuntimeError("Las copias de seguridad automáticas solo están disponibles para SQLite.")
    return Path(engine.url.database).resolve()


def directorio_backups() -> Path:
    """BACKUP_DIR puede apuntar a una carpeta sincronizada con la nube (OneDrive, Google Drive, Dropbox...)."""
    return Path(os.getenv("BACKUP_DIR", "backups")).resolve()


def dias_retencion() -> int:
    return int(os.getenv("BACKUP_RETENTION_DAYS", "14"))


def listar_backups(destino: Optional[Path] = None) -> List[Path]:
    destino = destino or directorio_backups()
    if not destino.exists():
        return []
    return sorted(destino.glob(f"{PREFIJO}*.db"))


def _fecha_backup(ruta: Path) -> Optional[datetime]:
    try:
        return datetime.strptime(ruta.stem[len(PREFIJO):], FORMATO_FECHA)
    except ValueError:
        return None


def limpiar_backups_antiguos(destino: Optional[Path] = None, retencion_dias: Optional[int] = None) -> List[Path]:
    """Borra las copias más antiguas que la retención. Nunca borra la copia más reciente."""
    retencion_dias = dias_retencion() if retencion_dias is None else retencion_dias
    backups = listar_backups(destino)
    limite = datetime.now() - timedelta(days=retencion_dias)
    borrados = []
    for b in backups[:-1]:
        fecha = _fecha_backup(b)
        if fecha and fecha < limite:
            b.unlink()
            borrados.append(b)
    return borrados


def crear_backup(destino: Optional[Path] = None, origen: Optional[Path] = None) -> Path:
    """Copia consistente de la BD con la API de backup de SQLite (segura con la app en marcha)."""
    origen = origen or ruta_bd()
    destino = destino or directorio_backups()
    destino.mkdir(parents=True, exist_ok=True)

    archivo = destino / f"{PREFIJO}{datetime.now().strftime(FORMATO_FECHA)}.db"
    src = sqlite3.connect(origen)
    dst = sqlite3.connect(archivo)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    limpiar_backups_antiguos(destino)
    logger.info("Copia de seguridad creada en %s", archivo)
    return archivo


def ultimo_backup_reciente(destino: Optional[Path] = None) -> bool:
    backups = listar_backups(destino)
    if not backups:
        return False
    fecha = _fecha_backup(backups[-1])
    return bool(fecha) and datetime.now() - fecha < timedelta(days=1)


async def bucle_backup_diario() -> None:
    """Tarea en segundo plano: hace una copia al arrancar si no hay una de las últimas 24 h y después una al día."""
    while True:
        try:
            if not ultimo_backup_reciente():
                await asyncio.to_thread(crear_backup)
        except Exception:
            logger.exception("Fallo al crear la copia de seguridad diaria")
        await asyncio.sleep(SEGUNDOS_DIA)
