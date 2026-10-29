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

## Exportar a Excel

- **Exportar a Excel (.xlsx)**: en el Diario eliges *desde* y *hasta* y pulsas *Descargar Excel* (o `GET /api/v1/exportar/excel?desde=2026-10-01&hasta=2026-10-31&idioma=es`). Sale una tabla con una fila por día: fecha, plan del día y calorías, proteínas, carbohidratos y grasas como *consumido/meta* (p. ej. `2100/2300`). La meta es la del plan de nutrición de ese día; verde si está a ±10%, ámbar a ±20%, rojo fuera, gris si es día libre. Máximo 366 días.
