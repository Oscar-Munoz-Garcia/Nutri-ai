"""Copia de seguridad manual o programada de nutri_ai.db.

Uso:  python scripts/backup_db.py [--destino CARPETA]
Programarlo a diario en Windows (Programador de tareas):
  schtasks /Create /SC DAILY /ST 03:00 /TN "NutriAI Backup" ^
    /TR "C:\\ruta\\nutri-ai\\.venv\\Scripts\\python.exe C:\\ruta\\nutri-ai\\scripts\\backup_db.py"
En Linux/macOS (cron):  0 3 * * * cd /ruta/nutri-ai && .venv/bin/python scripts/backup_db.py
"""
import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)  # DATABASE_URL por defecto es relativa a la raíz del proyecto

import app.core.config  # noqa: E402,F401  (carga el .env antes de leer DATABASE_URL/BACKUP_DIR)
from app.services import backup_service  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Copia de seguridad de la base de datos de NutriAI")
    parser.add_argument("--destino", help="Carpeta destino (por defecto BACKUP_DIR o ./backups)")
    args = parser.parse_args()

    archivo = backup_service.crear_backup(Path(args.destino).resolve() if args.destino else None)
    print(f"Copia creada: {archivo}")


if __name__ == "__main__":
    main()
