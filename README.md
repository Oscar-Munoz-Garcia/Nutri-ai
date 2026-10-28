# NutriAI - Asistente Inteligente de Nutrición, Despensa y Macros

## Privacidad multiusuario

Cada usuario solo ve y modifica su propio diario, despensa, recetas, perfil y analítica: todas las rutas `/api/v1/*` (salvo `/api/v1/auth/google` y `/api/v1/auth/config`) exigen `Authorization: Bearer <token>` y filtran por `usuario_id`. Sin token la API responde `401`. Los datos antiguos sin dueño (`usuario_id` vacío) se asignan al primer usuario registrado una sola vez (la primera vez que arranca esta versión); una fila sin dueño que aparezca después no se asigna a nadie.

**Acceso solo con Google.** La app no guarda contraseñas: se entra con "Iniciar sesión con Google" (`GOOGLE_CLIENT_ID` en `.env`). La primera vez se crea la cuenta y se muestra un cuestionario de alta (nombre y apellidos, edad, peso, altura, sexo, actividad y objetivo) que calcula las calorías y macros diarios. Las cuentas antiguas siguen funcionando si se entra con una cuenta de Google con el mismo correo.

## Copias de seguridad de `nutri_ai.db`

- **Automática:** mientras el servidor está en marcha se hace una copia al arrancar (si no hay una de las últimas 24 h) y otra cada día en `BACKUP_DIR` (por defecto `./backups`). Se guardan `BACKUP_RETENTION_DAYS` días (14 por defecto). Para tenerlas en la nube, apunta `BACKUP_DIR` a una carpeta sincronizada (OneDrive, Google Drive, Dropbox).
- **Manual:** `python scripts/backup_db.py [--destino CARPETA]`
- **Programada en Windows** (aunque el servidor esté apagado):
  ```
  schtasks /Create /SC DAILY /ST 03:00 /TN "NutriAI Backup" /TR "C:\ruta\nutri-ai\.venv\Scripts\python.exe C:\ruta\nutri-ai\scripts\backup_db.py"
  ```
- **Restaurar:** para el servidor y copia el `.db` elegido encima de `nutri_ai.db`.

## Excel, Google Sheets e importación masiva

- **Reporte mensual (.xlsx)**: botón *Descargar Excel* en el Diario o `GET /api/v1/exportar/excel?anio=2026&mes=10`. Incluye las pestañas *Diario*, *Despensa* y *KPIs & Gráficos* (fórmulas `SUMIFS`/`AVERAGEIF`, semáforo de cumplimiento con formato condicional y gráficos nativos de Excel).
- **Google Sheets**: pega `docs/google_sheets_apps_script.gs` en el Apps Script de tu hoja, impleméntalo como aplicación web y rellena `GOOGLE_SHEETS_WEBHOOK_URL` y `GOOGLE_SHEETS_WEBHOOK_SECRET` en el `.env`. El botón *Cerrar jornada* (o `POST /api/v1/sheets/cerrar-jornada`) envía el resumen del día; con `GOOGLE_SHEETS_HORA_CIERRE=23:55` se envía solo cada noche para todos los usuarios.
- **Importador**: arrastra un `.xlsx` o `.csv` a la pestaña Escáner (`POST /api/v1/importar`). La primera fila es la cabecera; detecta si son alimentos (despensa) o recetas.
