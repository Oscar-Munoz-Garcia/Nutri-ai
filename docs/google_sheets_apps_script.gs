/**
 * NutriAI Studio → Google Sheets
 *
 * 1. Crea (o abre) la hoja compartida de Google Sheets.
 * 2. Extensiones → Apps Script, pega este archivo y cambia SECRETO.
 * 3. Implementar → Nueva implementación → Tipo "Aplicación web".
 *    Ejecutar como: "Yo". Quién tiene acceso: "Cualquier usuario".
 * 4. Copia la URL /exec en el .env de NutriAI:
 *      GOOGLE_SHEETS_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
 *      GOOGLE_SHEETS_WEBHOOK_SECRET=<el mismo SECRETO>
 *
 * Cada envío crea o actualiza la fila (fecha, usuario) en la pestaña "Resumen diario".
 */
const SECRETO = 'cambia-este-secreto';
const NOMBRE_HOJA = 'Resumen diario';
const COLUMNAS = [
  'fecha', 'usuario', 'calorias', 'proteinas', 'carbohidratos', 'grasas',
  'meta_calorias', 'meta_proteinas', 'cumplimiento_calorias_pct', 'cumplimiento_proteinas_pct',
  'meta_cumplida', 'num_registros', 'actualizado'
];

function doPost(e) {
  const datos = JSON.parse(e.postData.contents);
  if (datos.secreto !== SECRETO) {
    return respuesta({ ok: false, error: 'Secreto incorrecto' });
  }

  const libro = SpreadsheetApp.getActiveSpreadsheet();
  const hoja = libro.getSheetByName(NOMBRE_HOJA) || libro.insertSheet(NOMBRE_HOJA);
  if (hoja.getLastRow() === 0) {
    hoja.appendRow(COLUMNAS);
    hoja.setFrozenRows(1);
    hoja.getRange(1, 1, 1, COLUMNAS.length).setFontWeight('bold').setBackground('#4981D4').setFontColor('#FFFFFF');
  }

  datos.actualizado = new Date();
  datos.meta_cumplida = datos.meta_cumplida ? 'Sí' : 'No';
  const fila = COLUMNAS.map(function (c) { return datos[c] !== undefined ? datos[c] : ''; });
  fila[0] = "'" + datos.fecha;  // la fecha se guarda como texto para poder buscarla después

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const valores = hoja.getRange(1, 1, hoja.getLastRow(), 2).getDisplayValues();
    let destino = -1;
    for (let i = 1; i < valores.length; i++) {
      if (valores[i][0] === datos.fecha && valores[i][1] === datos.usuario) { destino = i + 1; break; }
    }
    if (destino === -1) {
      hoja.appendRow(fila);
      destino = hoja.getLastRow();
    } else {
      hoja.getRange(destino, 1, 1, fila.length).setValues([fila]);
    }
    hoja.getRange(destino, 11).setBackground(datos.meta_cumplida === 'Sí' ? '#C8EFD4' : '#F6C9C9');
    return respuesta({ ok: true, fila: destino });
  } finally {
    lock.releaseLock();
  }
}

function respuesta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
