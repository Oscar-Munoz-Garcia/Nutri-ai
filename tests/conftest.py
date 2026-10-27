import os
import tempfile

# Configuración de entorno ANTES de importar la app: BD temporal para no tocar nutri_ai.db,
# usuario demo sin token para los tests heredados y sin bucle de backups en segundo plano.
_tmp_dir = tempfile.mkdtemp(prefix="nutri_ai_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp_dir, 'test.db')}"
os.environ["AUTH_DEMO_FALLBACK"] = "1"
os.environ["BACKUP_AUTO"] = "0"
os.environ["BACKUP_DIR"] = os.path.join(_tmp_dir, "backups")
