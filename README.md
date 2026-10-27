# NutriAI - Asistente Inteligente de Nutrición, Despensa y Macros
## Excel, Google Sheets e importación masiva

- **Reporte mensual (.xlsx)**: botón *Descargar Excel* en el Diario o `GET /api/v1/exportar/excel?anio=2026&mes=10`. Incluye las pestañas *Diario*, *Despensa* y *KPIs & Gráficos* (fórmulas `SUMIFS`/`AVERAGEIF`, semáforo de cumplimiento con formato condicional y gráficos nativos de Excel).
- **Google Sheets**: pega `docs/google_sheets_apps_script.gs` en el Apps Script de tu hoja, impleméntalo como aplicación web y rellena `GOOGLE_SHEETS_WEBHOOK_URL` y `GOOGLE_SHEETS_WEBHOOK_SECRET` en el `.env`. El botón *Cerrar jornada* (o `POST /api/v1/sheets/cerrar-jornada`) envía el resumen del día; con `GOOGLE_SHEETS_HORA_CIERRE=23:55` se envía solo cada noche para todos los usuarios.
- **Importador**: arrastra un `.xlsx` o `.csv` a la pestaña Escáner (`POST /api/v1/importar`). La primera fila es la cabecera; detecta si son alimentos (despensa) o recetas.
