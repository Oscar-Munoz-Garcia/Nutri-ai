// Idiomas de la interfaz (español / inglés).
// La interfaz se escribe en español y este módulo traduce al inglés el texto visible: cada nodo de texto
// y los atributos placeholder / title / aria-label, también los que se pintan después con JS (MutationObserver).
// Además traduce alert / confirm / prompt y expone window.t(texto) para textos que no están en el DOM (gráficas).
// Un elemento con translate="no" (mensajes del chat, nombres que escribe el usuario...) no se toca.
(function () {
    const CLAVE = "nutri_lang";
    const IDIOMAS = ["es", "en"];

    // ---------- TEXTOS FIJOS (español -> inglés) ----------
    const EN = {
        // Título de la página
        "NUTRI.AI Studio — Telemetría Nutricional": "NUTRI.AI Studio — Nutrition Telemetry",

        // Selector de idioma
        "Cambiar idioma": "Change language",

        // Acceso con Google
        "SISTEMA MULTIUSUARIO": "MULTI-USER SYSTEM",
        "Entra en NutriAI": "Sign in to NutriAI",
        "Usa tu cuenta de Google. Si es tu primera vez, te ayudamos a crear tu cuenta.": "Use your Google account. If it's your first time, we'll help you create your account.",
        "El inicio de sesión con Google no está configurado: falta GOOGLE_CLIENT_ID en el archivo .env del servidor.": "Google sign-in is not configured: GOOGLE_CLIENT_ID is missing from the server's .env file.",
        "No se pudo cargar Google. Revisa tu conexión y recarga la página.": "Couldn't load Google. Check your connection and reload the page.",
        "Error al iniciar sesión con Google": "Error signing in with Google",
        "Token de Google inválido o caducado.": "Invalid or expired Google token.",
        "El inicio de sesión con Google no está configurado (falta GOOGLE_CLIENT_ID).": "Google sign-in is not configured (GOOGLE_CLIENT_ID is missing).",
        "Tu cuenta de Google no tiene un correo verificado.": "Your Google account doesn't have a verified email.",
        "Debes iniciar sesión.": "You must sign in.",
        "Token inválido o expirado": "Invalid or expired token",
        "Usuario no encontrado": "User not found",

        // Primera vez y cuestionario de alta
        "PRIMERA VEZ EN NUTRIAI": "FIRST TIME ON NUTRIAI",
        "¡Hola! Es tu primera vez aquí": "Hi! It's your first time here",
        "No tienes cuenta todavía. Vamos a crearla: solo tienes que responder unas preguntas rápidas para calcular tus objetivos.": "You don't have an account yet. Let's create one: just answer a few quick questions so we can calculate your goals.",
        "Crear mi cuenta": "Create my account",
        "CREA TU CUENTA": "CREATE YOUR ACCOUNT",
        "Cuéntanos sobre ti": "Tell us about yourself",
        "Con estos datos calculamos tus objetivos diarios": "We use this to calculate your daily goals",
        "Nombre": "First name",
        "Apellidos": "Last name",
        "Edad": "Age",
        "Peso (kg)": "Weight (kg)",
        "Altura (cm)": "Height (cm)",
        "Sexo": "Sex",
        "Hombre": "Male",
        "Mujer": "Female",
        "Actividad física": "Physical activity",
        "Sedentario": "Sedentary",
        "Ligera (1-3 días/sem)": "Light (1-3 days/wk)",
        "Moderada (3-5 días/sem)": "Moderate (3-5 days/wk)",
        "Intensa (6-7 días/sem)": "Intense (6-7 days/wk)",
        "Objetivo": "Goal",
        "Perder grasa": "Lose fat",
        "Mantenerme": "Maintain",
        "Ganar músculo": "Build muscle",
        "Empezar": "Get started",
        "Revisa los datos: hay algún valor fuera de rango.": "Check your details: some value is out of range.",
        "No se pudo guardar el perfil": "Couldn't save the profile",

        // Cabecera y navegación
        "Digital Studio // Multiusuario": "Digital Studio // Multi-user",
        "Cambiar modo claro / oscuro": "Toggle light / dark mode",
        "Salir ↵": "Log out ↵",
        "01 / Diario": "01 / Diary",
        "02 / Recetas": "02 / Recipes",
        "03 / Escáner": "03 / Scanner",
        "04 / Agente": "04 / Agent",
        "05 / Perfil": "05 / Profile",
        "06 / Versus": "06 / Versus",

        // Diario
        "TELEMETRÍA DIARIA": "DAILY TELEMETRY",
        "Energía & Macros": "Energy & Macros",
        "⚙ Metas": "⚙ Goals",
        "Consumido": "Consumed",
        "Faltan / Meta": "Left / Goal",
        "PROTEÍNAS": "PROTEIN",
        "CARBOHIDRATOS": "CARBS",
        "GRASAS": "FAT",
        "restantes)": "left)",
        "Historial del Día": "Day's Log",
        "🔄 Actualizar": "🔄 Refresh",
        "Sin consumos registrados hoy.": "Nothing logged today.",
        "Sin consumos registrados este día.": "Nothing logged on this day.",
        // Selector de día del Diario (ayer o cualquier fecha pasada)
        "Día anterior": "Previous day",
        "Día siguiente": "Next day",
        "Hoy": "Today",
        "Ayer": "Yesterday",
        "Elige un día para consultarlo o registrar comidas": "Pick a day to view it or log meals",
        "📅 Estás viendo otro día:": "📅 You're viewing another day:",
        "Lo que añadas se guardará en ese día.": "Anything you add will be saved to that day.",
        "Plan de ese día:": "That day's plan:",
        "Metas del plan de ese día:": "That day's plan goals:",
        "🍽 Ese día fue libre: no cuenta para tus metas ni tu racha": "🍽 That was a day off: it doesn't count toward your goals or streak",
        "Abrir este día en el Diario": "Open this day in the Diary",
        "Eliminar registro": "Delete entry",
        "¿Deseas eliminar este registro de comida?": "Do you want to delete this food entry?",
        "REPORTES": "REPORTS",
        "⬇ Descargar Excel": "⬇ Download Excel",
        "Exportar a Excel": "Export to Excel",
        "Una fila por día con calorías y macros consumidos / meta de tu plan (p. ej. 2100/2300).": "One row per day with calories and macros consumed / your plan's goal (e.g. 2100/2300).",
        "Desde": "From",
        "Hasta": "To",
        "❌ La fecha de inicio no puede ser posterior a la de fin.": "❌ The start date can't be after the end date.",
        "La fecha de inicio no puede ser posterior a la de fin.": "The start date can't be after the end date.",
        "⏳ Generando reporte...": "⏳ Generating report...",
        "Error al generar el Excel": "Error generating the Excel file",
        "No se pudo sincronizar": "Couldn't sync",

        // Planes de nutrición
        "⚙ Plan": "⚙ Plan",
        "Plan de hoy:": "Today's plan:",
        "Cambiar el plan de un día": "Change a day's plan",
        "Plan de cada día": "Plan for each day",
        "Semana anterior": "Previous week",
        "Semana siguiente": "Next week",
        "Elige otro plan solo para ese día. La semana tipo se cambia en Perfil.": "Pick another plan just for that day. Your usual week is set in Profile.",
        "Gestionar planes →": "Manage plans →",
        // Días libres
        "🍽 Hoy es día libre: no cuenta para tus metas ni tu racha": "🍽 Today is a day off: it doesn't count toward your goals or streak",
        "🍽 Día libre": "🍽 Day off",
        "🍽 Quitar día libre": "🍽 Remove day off",
        "Comes fuera: este día no cuenta para tus metas": "Eating out: this day doesn't count toward your goals",
        "🍽 marca un día libre (comida fuera): no cuenta para tus metas ni rompe la racha.": "🍽 marks a day off (eating out): it doesn't count toward your goals or break your streak.",
        "Marcar como día libre": "Mark as day off",
        "Quitar día libre": "Remove day off",
        "No se pudo cambiar el día libre.": "Couldn't change the day off.",
        "3. Días libres": "3. Days off",
        "Un día libre (por ejemplo, una comida fuera) no cuenta para tus metas ni rompe la racha. Lo marcas desde el Diario.": "A day off (for example, eating out) doesn't count toward your goals or break your streak. You mark it from the Diary.",
        "Días libres por semana": "Days off per week",
        "Día libre": "Day off",
        "Metas del plan de hoy:": "Today's plan goals:",
        "Volver al plan de la semana": "Back to the weekly plan",
        "Plan principal": "Main plan",
        "PLANES DE NUTRICIÓN": "NUTRITION PLANS",
        "Tus planes": "Your plans",
        "+ Nuevo plan": "+ New plan",
        "Crea tantos planes como quieras, por ejemplo uno para los días de entrenamiento y otro para los de descanso, y elige cuál toca cada día de la semana. Desde el Diario (⚙ Plan) puedes cambiar el de un día concreto.": "Create as many plans as you like, for example one for training days and another for rest days, and choose which one applies on each weekday. From the Diary (⚙ Plan) you can change it for a specific day.",
        "Principal": "Main",
        "Editar plan": "Edit plan",
        "Eliminar plan": "Delete plan",
        "Nuevo plan": "New plan",
        "Nombre del plan": "Plan name",
        "Ej: Entrenamiento": "E.g. Training",
        "Calorías (kcal) · se calculan con los macros, puedes ajustarlas": "Calories (kcal) · calculated from the macros, you can adjust them",
        "Guardar plan": "Save plan",
        "Semana tipo": "Usual week",
        "Lunes": "Monday",
        "Martes": "Tuesday",
        "Miércoles": "Wednesday",
        "Jueves": "Thursday",
        "Viernes": "Friday",
        "Sábado": "Saturday",
        "Domingo": "Sunday",
        "Semana tipo guardada": "Usual week saved",
        "No se pudo guardar la semana": "Couldn't save the week",
        "Revisa los datos del plan: hay algún valor fuera de rango.": "Check the plan details: some value is out of range.",
        "¿Eliminar este plan? Los días que lo usaban pasarán al plan principal.": "Delete this plan? The days that used it will switch to the main plan.",
        "El plan principal no se puede borrar: son las metas de tu perfil.": "The main plan can't be deleted: it holds your profile goals.",
        "Plan no encontrado": "Plan not found",

        // Metas rápidas
        "Establecer Metas Diarias": "Set Daily Goals",
        "Meta Calorías (kcal)": "Calorie goal (kcal)",
        "Meta Proteínas (g)": "Protein goal (g)",
        "Meta Carbohidratos (g)": "Carbs goal (g)",
        "Meta Grasas (g)": "Fat goal (g)",
        "Guardar Metas": "Save Goals",

        // Calendario de constancia y registro rápido (dashboard360.js)
        "Calendario de constancia": "Consistency calendar",
        "Sin datos": "No data",
        "Ambas metas": "Both goals",
        "Mejor racha": "Best streak",
        "Días cumplidos": "Days on target",
        "Cumplimiento": "Success rate",
        "Registro rápido por voz": "Quick voice log",
        "Registro rápido": "Quick log",
        "Cerrar": "Close",
        "Dictar": "Dictate",
        "Quitar": "Remove",
        "Pulsa y dicta, por ejemplo: «Desayuno: 3 huevos cocidos y 80g de avena»": "Tap and speak, for example: “Breakfast: 3 boiled eggs and 80g of oats”",
        "Tu navegador no admite dictado por voz; escríbelo abajo.": "Your browser doesn't support voice dictation; type it below.",
        "Desayuno: 3 huevos cocidos y 80g de avena": "Breakfast: 3 boiled eggs and 80g of oats",
        "Calcular macros": "Calculate macros",
        "Calculando…": "Calculating…",
        "Escuchando…": "Listening…",
        "Permiso de micrófono denegado.": "Microphone permission denied.",
        "No te he entendido, prueba otra vez.": "I didn't catch that, try again.",
        "Revisa el texto o pulsa el micro para repetir.": "Check the text or tap the mic to try again.",
        "No se pudo interpretar el texto.": "Couldn't interpret the text.",
        "📦 despensa": "📦 pantry",
        "✨ estimado IA": "✨ AI estimate",
        "⚠ rellena a mano": "⚠ fill in manually",
        "Prot": "Prot",
        "Grasas": "Fat",
        "Error al guardar, reintentar": "Error saving, try again",
        "No se pudo contactar con Groq; revisa los valores antes de guardar.": "Couldn't reach Groq; check the values before saving.",
        "Sin GROQ_API_KEY solo se calculan alimentos de tu despensa indicados en gramos.": "Without GROQ_API_KEY only pantry foods given in grams are calculated.",

        // Recetas
        "CATÁLOGO EDITORIAL": "EDITORIAL CATALOG",
        "Recetas & Preparación": "Recipes & Prep",
        "+ Nueva": "+ New",
        "Nombre de la Receta": "Recipe name",
        "Ej: Bowl de Avena y Proteína": "E.g. Oat & Protein Bowl",
        "Añadir desde Despensa Virtual": "Add from Virtual Pantry",
        "-- Seleccionar de despensa --": "-- Select from pantry --",
        "Gramos": "Grams",
        "+ Sumar": "+ Add",
        "Calorías (kcal)": "Calories (kcal)",
        "Proteínas (g)": "Protein (g)",
        "Carbohidratos (g)": "Carbs (g)",
        "Grasas (g)": "Fat (g)",
        "Utensilios (separados por coma)": "Utensils (comma-separated)",
        "Air Fryer, Sartén": "Air Fryer, Frying pan",
        "Descripción": "Description",
        "Instrucciones breves...": "Short instructions...",
        "Pasos (uno por línea, \"5 min\" crea temporizador)": "Steps (one per line, \"5 min\" creates a timer)",
        "Hervir el arroz 20 min Dorar el pollo 8 min": "Boil the rice 20 min\nBrown the chicken 8 min",
        "Tiempo (min)": "Time (min)",
        "Guardar Receta": "Save Recipe",
        "Cargando recetas...": "Loading recipes...",
        "Sin recetas registradas.": "No recipes yet.",
        "Sin descripción": "No description",
        "GRASAS:": "FAT:",
        "👨‍🍳 Modo cocina": "👨‍🍳 Cooking mode",
        "[ + CONSUMIR ]": "[ + EAT ]",
        "Selecciona un ingrediente de tu despensa e indica la cantidad en gramos.": "Pick an ingredient from your pantry and enter the amount in grams.",
        "✅ Receta consumida e incorporada a tus macros diarios.": "✅ Recipe eaten and added to your daily macros.",
        "Error al consumir la receta.": "Error logging the recipe.",
        "Receta no encontrada.": "Recipe not found.",

        // Modo cocina (dashboard360.js)
        "No se encontró la receta.": "Recipe not found.",
        "Modo cocina": "Cooking mode",
        "Salir ✕": "Exit ✕",
        "Ingredientes": "Ingredients",
        "Esta receta no tiene ingredientes detallados.": "This recipe has no detailed ingredients.",
        "Pasos": "Steps",
        "Esta receta no tiene pasos. Añádelos al crearla para usar el modo cocina.": "This recipe has no steps. Add them when creating it to use cooking mode.",
        "Temporizadores": "Timers",
        "Receta completa": "Full recipe",
        "← Anterior": "← Previous",
        "Siguiente paso →": "Next step →",
        "¡Listo! 🍽": "Done! 🍽",
        "¡Tiempo!": "Time's up!",
        "Sin temporizadores activos.": "No active timers.",
        "NutriAI · Temporizador": "NutriAI · Timer",

        // Escáner
        "VISIÓN MULTIMODAL GROQ": "GROQ MULTIMODAL VISION",
        "Escáner OCR de Tablas": "Nutrition Label OCR Scanner",
        "Fotografiar / Capturar": "Take photo / Capture",
        "Abre la cámara del móvil en tiempo real": "Opens your phone camera in real time",
        "Procesar con Groq Vision": "Process with Groq Vision",
        "⏳ Extrayendo datos con Groq Vision...": "⏳ Extracting data with Groq Vision...",
        "❌ No se pudieron leer los macros.": "❌ Couldn't read the macros.",
        "❌ Error de red.": "❌ Network error.",
        "Recetas": "Recipes",
        "Arroz blanco cocido": "Cooked white rice",
        "Pechuga de pollo a la plancha": "Grilled chicken breast",
        "Aguacate": "Avocado",
        "OPEN FOOD FACTS": "OPEN FOOD FACTS",
        "Código de Barras": "Barcode",
        "📷 Escanear con la cámara": "📷 Scan with camera",
        "■ Detener cámara": "■ Stop camera",
        "O escribe el código (EAN-13)": "Or type the code (EAN-13)",
        "Buscar": "Search",
        "gramos": "grams",
        "+ Despensa": "+ Pantry",
        "+ Diario": "+ Diary",
        "❌ El código debe tener entre 8 y 14 dígitos.": "❌ The code must have between 8 and 14 digits.",
        "El código de barras debe tener entre 8 y 14 dígitos.": "The barcode must have between 8 and 14 digits.",
        "Producto no encontrado en Open Food Facts.": "Product not found on Open Food Facts.",
        "No se pudo cargar el lector de códigos.": "Couldn't load the barcode reader.",
        "❌ La cámara necesita HTTPS (o localhost). Escribe el código a mano.": "❌ The camera needs HTTPS (or localhost). Type the code manually.",
        "Apunta al código de barras del envoltorio...": "Point at the barcode on the package...",
        "Despensa Virtual": "Virtual Pantry",
        "Refrescar": "Refresh",
        "Cargando despensa...": "Loading pantry...",
        "Tu despensa virtual está vacía.": "Your virtual pantry is empty.",
        "Quitar de despensa": "Remove from pantry",
        "¿Deseas eliminar este ingrediente de tu despensa?": "Do you want to remove this ingredient from your pantry?",
        "Ítem no encontrado en despensa": "Item not found in pantry",
        "RECETAS VS DESPENSA": "RECIPES VS PANTRY",
        "Lista de la Compra": "Shopping List",
        "Lista de la compra": "Shopping list",
        "Marca las recetas que vais a cocinar la próxima semana y cuántas veces.": "Tick the recipes you'll cook next week and how many times.",
        "🛒 Generar lista de la compra": "🛒 Generate shopping list",
        "Crea recetas con ingredientes en la pestaña Recetas.": "Create recipes with ingredients in the Recipes tab.",
        "sin ingredientes guardados": "no saved ingredients",
        "Veces que la cocinaréis": "Times you'll cook it",
        "Marca al menos una receta.": "Tick at least one recipe.",
        "✅ Tenéis todo lo necesario en la despensa.": "✅ You have everything you need in the pantry.",
        "Copiar lista": "Copy list",
        "Nada que mostrar.": "Nothing to show.",
        "Lista copiada al portapapeles.": "List copied to clipboard.",

        // Agente
        "👋 **NutriAI Agent**: Puedes pedirme calcular raciones exactas o decirme *\"He comido 200g de pollo\"* para sumarlo en vivo a tu diario.": "👋 **NutriAI Agent**: You can ask me to calculate exact portions or tell me *\"I ate 200g of chicken\"* to add it to your diary live.",
        "Ej: He comido 200g de pechuga...": "E.g. I ate 200g of chicken breast...",
        "Enviar": "Send",
        "❌ Error de conexión.": "❌ Connection error.",

        // Perfil
        "CONFIGURACIÓN DE USUARIO": "USER SETTINGS",
        "Perfil & Límites Diarios": "Profile & Daily Limits",
        "Manual Macros": "Manual Macros",
        "MANUAL CALORIAS": "MANUAL CALORIES",
        "1. Datos Antropométricos": "1. Body Measurements",
        "Género": "Gender",
        "Actividad": "Activity",
        "Ligero": "Light",
        "Moderado": "Moderate",
        "Intenso": "Intense",
        "2. Método de Objetivos Diarios": "2. Daily Goal Method",
        "⚙️ Macros Exactos (Personalizado)": "⚙️ Exact Macros (Custom)",
        "🔥 Calorías Totales (Reparto automático)": "🔥 Total Calories (Auto split)",
        "🧮 Calculadora Automática (Mifflin-St Jeor)": "🧮 Automatic Calculator (Mifflin-St Jeor)",
        "Define los gramos exactos deseados para todos los días:": "Set the exact grams you want for every day:",
        "Define los gramos exactos de tu plan principal:": "Set the exact grams for your main plan:",
        "Estos objetivos son tu plan principal. Puedes crear más planes (entrenamiento, descanso...) justo debajo.": "These targets are your main plan. You can create more plans (training, rest...) right below.",
        "Introduce las calorías totales diarias. Se repartirán automáticamente:": "Enter your total daily calories. They'll be split automatically:",
        "Límite Calorías Totales (kcal)": "Total Calorie Limit (kcal)",
        "💡 Se calcularán automáticamente tus necesidades metabólicas diarias y gramos óptimos según tu peso, altura, edad y nivel de actividad.": "💡 Your daily metabolic needs and optimal grams will be calculated automatically from your weight, height, age and activity level.",
        "Guardar Perfil & Actualizar Diario": "Save Profile & Update Diary",
        "✅ Perfil y límites diarios actualizados con éxito.": "✅ Profile and daily limits updated successfully.",
        "Define los macros de tu plan principal:": "Set the macros for your main plan:",
        "Usar %": "Use %",
        "Usar gramos": "Use grams",
        "Proteínas (%)": "Protein (%)",
        "Carbs (%)": "Carbs (%)",
        "Grasas (%)": "Fat (%)",
        "Carbos": "Carbs",
        "Calorías": "Calories",
        "Macros repartidos manteniendo sus porcentajes.": "Macros split keeping their percentages.",
        "⚠️ Los porcentajes pasan del 100 %.": "⚠️ Percentages add up to more than 100 %.",
        "✅ Perfil actualizado": "✅ Profile updated",
        "Esto actualiza solo el plan principal, puedes crear más planes en 'Tus Planes'.": "This only updates your main plan, you can create more plans in 'Your plans'.",
        "❌ No se pudo guardar el perfil.": "❌ Couldn't save the profile.",
        "TELEMETRÍA METABÓLICA": "METABOLIC TELEMETRY",
        "Metabolismo Real (TDEE Dinámico)": "Real Metabolism (Dynamic TDEE)",
        "Pesar": "Log weight",
        "Pésate 2-3 veces por semana, en ayunas. La app cruza tu tendencia de peso con lo que registras en el diario.": "Weigh yourself 2-3 times a week, before eating. The app compares your weight trend with what you log in the diary.",
        "TDEE Real": "Real TDEE",
        "kcal/día": "kcal/day",
        "TDEE Fórmula": "Formula TDEE",
        "Tendencia": "Trend",
        "kg/sem": "kg/wk",
        "Ingesta Media": "Average Intake",
        "Peso (últimos 28 días) y recta de regresión": "Weight (last 28 days) and regression line",
        "Aún no hay pesajes en las últimas 4 semanas.": "No weigh-ins in the last 4 weeks yet.",
        "❌ No se pudo guardar el pesaje.": "❌ Couldn't save the weigh-in.",
        "Fecha inválida, usa el formato YYYY-MM-DD.": "Invalid date, use the YYYY-MM-DD format.",
        "TELEMETRÍA HISTÓRICA": "HISTORICAL TELEMETRY",
        "Análisis de Tendencias & Macros": "Trends & Macros Analysis",
        "7 Días": "7 Days",
        "14 Días": "14 Days",
        "30 Días": "30 Days",
        "Promedio Calórico": "Average Calories",
        "Promedio Proteína": "Average Protein",
        "g/día": "g/day",
        "Evolución Diaria (kcal & g)": "Daily Progress (kcal & g)",
        "Distribución Real de Macronutrientes": "Actual Macronutrient Split",
        "Proteínas": "Protein",
        "Carbohidratos": "Carbs",
        "ZONA DE PELIGRO": "DANGER ZONE",
        "Eliminar cuenta": "Delete account",
        "Se borran para siempre tu perfil, diario, despensa, recetas, pesajes y amistades. No se puede deshacer.": "Your profile, diary, pantry, recipes, weigh-ins and friendships are deleted forever. This can't be undone.",
        "Eliminar mi cuenta": "Delete my account",
        "Esto borrará tu cuenta y TODOS tus datos para siempre.": "This will delete your account and ALL your data forever.",
        "Escribe ELIMINAR para confirmar:": "Type DELETE to confirm:",
        "ELIMINAR": "DELETE",
        "No se ha eliminado nada: tenías que escribir ELIMINAR.": "Nothing was deleted: you had to type DELETE.",
        "No se pudo eliminar la cuenta": "Couldn't delete the account",
        "Tu cuenta se ha eliminado. ¡Hasta pronto!": "Your account has been deleted. See you soon!",

        // Versus y amigos
        "GAMIFICACIÓN PRIVADA": "PRIVATE GAMIFICATION",
        "Duelo Semanal": "Weekly Duel",
        "Solo compites con tus amigos. Cada día puntúa de 0 a 100: la mitad por clavar las calorías (100% dentro de ±10% de tu meta, 0% a partir de ±30%) y la otra mitad por llegar a tu proteína. Un día sin registros cuenta 0. De tus amigos solo ves la puntuación, nunca lo que comen.": "You only compete with your friends. Each day scores 0 to 100: half for hitting your calories (100% within ±10% of your goal, 0% from ±30%) and half for reaching your protein. A day with no entries counts as 0. You only see your friends' scores, never what they eat.",
        "(tú)": "(you)",
        "Agrega a un amigo abajo para empezar el duelo.": "Add a friend below to start the duel.",
        "❌ No se pudo cargar el duelo.": "❌ Couldn't load the duel.",
        "TU CÍRCULO": "YOUR CIRCLE",
        "Amigos": "Friends",
        "Usuario o email": "Username or email",
        "Agregar": "Add",
        "Aceptar": "Accept",
        "Rechazar": "Decline",
        "Cancelar": "Cancel",
        "Solicitudes enviadas": "Sent requests",
        "· pendiente": "· pending",
        "Todavía no tienes amigos agregados.": "You haven't added any friends yet.",
        "¿Eliminar a esta persona de tus amigos?": "Remove this person from your friends?",
        "Ya sois amigos: tenía una solicitud tuya pendiente.": "You're now friends: they had a pending request to you.",
        "Solicitud enviada.": "Request sent.",
        "No existe ningún usuario con ese nombre o email.": "There's no user with that name or email.",
        "No puedes agregarte a ti mismo.": "You can't add yourself.",
        "Solicitud no encontrada": "Request not found",
        "Amigo no encontrado": "Friend not found",

        // Comidas del día y botón «+» para añadir alimentos por gramos (comidas.js)
        "Comidas al día": "Meals per day",
        "Ponles el nombre que quieras, por ejemplo Pre-entreno.": "Name them however you like, e.g. Pre-workout.",
        "Desayuno": "Breakfast",
        "Almuerzo": "Mid-morning snack",
        "Comida": "Lunch",
        "Merienda": "Afternoon snack",
        "Cena": "Dinner",
        "Recena": "Late snack",
        "Pre-entreno": "Pre-workout",
        "Post-entreno": "Post-workout",
        "Sin comida asignada": "No meal assigned",
        "Añadir a esta comida": "Add to this meal",
        "Añadir alimentos": "Add foods",
        "Añadir a": "Add to",
        "Añadir": "Add",
        "Añadir 1 alimento": "Add 1 food",
        "Elegir comida": "Choose meal",
        "Busca un alimento: arroz, pollo, tomate…": "Search for a food: rice, chicken, tomato…",
        "Crear a mano:": "Add manually:",
        "Ver en la rueda": "Show in the chart",
        "Valores por 100 g": "Values per 100 g",
        "Ver total": "Show total",
        "Total": "Total",
        "% de cada macro sobre el total de gramos de macros.": "% of each macro over the total grams of macros.",
        "Busca y añade cada alimento con sus gramos, por ejemplo 200 g de arroz y 150 g de pollo.": "Search and add each food with its grams, for example 200 g of rice and 150 g of chicken.",
        "No se pudo guardar. Revisa la conexión y vuelve a intentarlo.": "Couldn't save. Check your connection and try again."
    };

    // ---------- TEXTOS CON DATOS (expresión regular -> inglés) ----------
    const tr = (s) => traducirNucleo(s) ?? s;
    const PATRONES = [
        [/^¡Hola, (.+)! Es tu primera vez aquí$/, "Hi, $1! It's your first time here"],
        [/^de (.+) kcal$/, "of $1 kcal"],
        [/^🔥 (.+) kcal · P: (.+)g · C: (.+)g · G: (.+)g$/, "🔥 $1 kcal · P: $2g · C: $3g · F: $4g"],
        [/^(.+) kcal\/100g · P:(.+)g C:(.+)g G:(.+)g$/, "$1 kcal/100g · P:$2g C:$3g F:$4g"],
        [/^Por 100 g: (.+) kcal · P (.+)g · C (.+)g · G (.+)g$/, "Per 100 g: $1 kcal · P $2g · C $3g · F $4g"],
        [/^(.+) kcal · P (.+)g · C (.+)g · G (.+)g$/, "$1 kcal · P $2g · C $3g · F $4g"],
        [/^(.*) \((.+)g dispon\.\)$/, "$1 ($2g avail.)"],
        [/^Ingredientes: (.*)$/, "Ingredients: $1"],
        [/^⚠️ Las calorías pasan de (\d+) a (\d+) kcal\.$/, "⚠️ Calories go from $1 to $2 kcal."],
        [/^⚠️ Los otros macros ya superan esas calorías: (.+) en 0 g\.$/, (_, m) => `⚠️ The other macros already exceed those calories: ${tr(m)} at 0 g.`],
        [/^Se completa solo: (.+)$/, (_, m) => `Fills in automatically: ${tr(m)}`],
        [/^Ingredientes \((\d+)\/(\d+)\)$/, "Ingredients ($1/$2)"],
        // TDEE dinámico (mensajes del servidor)
        [/^Faltan datos para calcular tu TDEE real: (.+)\. Mientras tanto se muestra el estimado por fórmula\.$/,
            (_, faltan) => `Not enough data to calculate your real TDEE: ${faltan.split(", ").map(tr).join(", ")}. Meanwhile the formula estimate is shown.`],
        [/^(\d+) pesaje\(s\) más$/, "$1 more weigh-in(s)"],
        [/^pesajes separados al menos (\d+) días$/, "weigh-ins at least $1 days apart"],
        [/^(\d+) día\(s\) más con comidas registradas$/, "$1 more day(s) with logged meals"],
        [/^Con (.+) kcal\/día de media tu peso varía (.+) kg\/semana\.$/, "At an average of $1 kcal/day your weight changes $2 kg/week."],
        [/^Fiabilidad del ajuste \(R²\): (.+)\.$/, "Fit reliability (R²): $1."],
        [/^\((\d+) pesajes, (\d+)\/(\d+) días registrados\)$/, "($1 weigh-ins, $2/$3 days logged)"],
        // Versus y amigos
        [/^(\d+)\/(\d+) días ≥90%$/, "$1/$2 days ≥90%"],
        [/^vs semana pasada \((.+)%\): (.+)$/, "vs last week ($1%): $2"],
        [/^Solicitudes recibidas \((\d+)\)$/, "Received requests ($1)"],
        [/^Tus amigos \((\d+)\)$/, "Your friends ($1)"],
        [/^(.+) ya es tu amigo\.$/, "$1 is already your friend."],
        [/^Ya enviaste una solicitud a (.+)\.$/, "You already sent a request to $1."],
        // Escáner y reportes
        [/^✅ Alimento detectado: (.+) \((.+) kcal\/100g\)$/, "✅ Food detected: $1 ($2 kcal/100g)"],
        [/^✅ Descargado (.+)$/, "✅ Downloaded $1"],
        [/^⏳ Buscando (.+) en Open Food Facts\.\.\.$/, "⏳ Looking up $1 on Open Food Facts..."],
        [/^✅ (.+) \((.+) g\) añadido a la despensa\.$/, "✅ $1 ($2 g) added to the pantry."],
        [/^✅ (.+) \((.+) g\) registrado en el diario\.$/, "✅ $1 ($2 g) logged in the diary."],
        [/^❌ No se pudo abrir la cámara: (.*)$/, "❌ Couldn't open the camera: $1"],
        [/^(\d+) ingredientes$/, "$1 ingredients"],
        [/^tienes (.+) g$/, "you have $1 g"],
        [/^Falta por comprar \((\d+)\)$/, "To buy ($1)"],
        [/^Ya en la despensa \((\d+)\)$/, "Already in the pantry ($1)"],
        [/^Sin ingredientes guardados, no se han podido comparar: (.*)\.$/, "No saved ingredients, couldn't compare: $1."],
        // Calendario de constancia, registro rápido y modo cocina (dashboard360.js)
        [/^🔥 (\d+) días? de racha$/, (_, n) => `🔥 ${n}-day streak`],
        [/^Meta: (.+) kcal ±10%$/, "Goal: $1 kcal ±10%"],
        [/^y (.+) g proteína ±10%$/, "and $1 g protein ±10%"],
        [/^✅ Receta añadida al día (\d{4}-\d{2}-\d{2})\.$/, "✅ Recipe added to $1."],
        [/^Días libres esta semana: (\d+)\/(\d+)$/, "Days off this week: $1/$2"],
        [/^Ya has llegado a tu límite de días libres esta semana \((\d+)\)\. Puedes cambiarlo en tu perfil\.$/, "You've reached your days-off limit for this week ($1). You can change it in your profile."],
        [/^(.+) · 🍽 día libre$/, "$1 · 🍽 day off"],
        [/^(.+) ✓ metas cumplidas$/, "$1 ✓ goals met"],
        [/^(.+) · sin registros$/, "$1 · no entries"],
        [/^Guardar (\d+) en el diario$/, "Save $1 to diary"],
        [/^Añadir (\d+) alimentos$/, "Add $1 foods"],
        [/^Comida (\d+)$/, "Meal $1"],
        [/^G · (\d+)%$/, "F · $1%"],
        [/^⏱ Temporizador (.+) min$/, "⏱ Timer $1 min"],
        [/^Receta (\d+) min$/, "Recipe $1 min"],
        [/^Paso (\d+)$/, "Step $1"],
        [/^(.+): ¡tiempo!$/, (_, e) => `${tr(e)}: time's up!`],
        // Mensajes con prefijo de estado: "✅ " / "❌ " / "⚠ " + texto conocido (p. ej. errores del servidor)
        [/^(✅|❌|⚠|⏳) (.+)$/, (todo, emoji, resto) => { const t = traducirNucleo(resto); return t == null ? todo : `${emoji} ${t}`; }]
    ];

    // ---------- ESTADO ----------
    function idiomaInicial() {
        try {
            const guardado = localStorage.getItem(CLAVE);
            if (IDIOMAS.includes(guardado)) return guardado;
        } catch (e) {}
        const navegador = (navigator.languages && navigator.languages[0]) || navigator.language || "es";
        return navegador.toLowerCase().startsWith("es") ? "es" : "en";
    }

    let idioma = idiomaInicial();
    document.documentElement.lang = idioma;

    // Devuelve la traducción del texto ya normalizado, o null si no hay
    function traducirNucleo(nucleo) {
        if (Object.prototype.hasOwnProperty.call(EN, nucleo)) return EN[nucleo];
        for (const [re, reemplazo] of PATRONES) {
            if (re.test(nucleo)) return nucleo.replace(re, reemplazo);
        }
        return null;
    }

    // Traduce un texto conservando los espacios de los extremos; en español lo devuelve tal cual
    function t(texto) {
        if (idioma === "es" || texto == null) return texto;
        const cadena = String(texto);
        const m = cadena.match(/^(\s*)([\s\S]*?)(\s*)$/);
        const nucleo = m[2].replace(/\s+/g, " ");
        if (!nucleo) return cadena;
        const traducido = traducirNucleo(nucleo);
        return traducido == null ? cadena : m[1] + traducido + m[3];
    }

    // Para alert / confirm / prompt: cada línea por separado
    const tLineas = (texto) => idioma === "es" ? texto : String(texto ?? "").split("\n").map(t).join("\n");

    // ---------- DOM ----------
    const EXCLUIR = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "NOSCRIPT"]);
    const ATRIBUTOS = ["placeholder", "title", "aria-label"];
    const textos = new WeakMap();      // nodo de texto -> { es, puesto }
    const atributos = new WeakMap();   // elemento -> { [atributo]: { es, puesto } }

    function excluido(el) {
        return !el || EXCLUIR.has(el.tagName) || !!(el.closest && el.closest('[translate="no"]'));
    }

    function procesarTexto(nodo) {
        if (excluido(nodo.parentElement)) return;
        let reg = textos.get(nodo);
        // Si el texto cambió desde la última vez, lo nuevo es el original en español
        if (!reg || nodo.data !== reg.puesto) {
            reg = { es: nodo.data };
            textos.set(nodo, reg);
        }
        const nuevo = t(reg.es);
        reg.puesto = nuevo;
        if (nodo.data !== nuevo) nodo.data = nuevo;
    }

    function procesarAtributos(el) {
        let regs = null;
        for (const nombre of ATRIBUTOS) {
            const valor = el.getAttribute(nombre);
            if (valor == null) continue;
            regs = regs || atributos.get(el) || {};
            let reg = regs[nombre];
            if (!reg || valor !== reg.puesto) reg = regs[nombre] = { es: valor };
            const nuevo = t(reg.es);
            reg.puesto = nuevo;
            if (valor !== nuevo) el.setAttribute(nombre, nuevo);
        }
        if (regs) atributos.set(el, regs);
    }

    function procesarArbol(raiz) {
        if (raiz.nodeType === Node.TEXT_NODE) return procesarTexto(raiz);
        if (raiz.nodeType !== Node.ELEMENT_NODE || raiz.closest('[translate="no"]')) return;
        // En un <textarea> el contenido es del usuario, pero su placeholder sí se traduce
        procesarAtributos(raiz);
        if (EXCLUIR.has(raiz.tagName)) return;
        const recorrido = document.createTreeWalker(raiz, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
            acceptNode: (n) => {
                if (n.nodeType !== Node.ELEMENT_NODE) return NodeFilter.FILTER_ACCEPT;
                if (n.getAttribute("translate") === "no") return NodeFilter.FILTER_REJECT;
                if (EXCLUIR.has(n.tagName)) { procesarAtributos(n); return NodeFilter.FILTER_REJECT; }
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        let n;
        while ((n = recorrido.nextNode())) {
            if (n.nodeType === Node.TEXT_NODE) procesarTexto(n);
            else procesarAtributos(n);
        }
    }

    // Lo que se pinta después (innerHTML, innerText...) se traduce al vuelo
    new MutationObserver((cambios) => {
        for (const c of cambios) {
            if (c.type === "childList") c.addedNodes.forEach(procesarArbol);
            else if (c.type === "characterData") procesarTexto(c.target);
            else if (c.type === "attributes") procesarAtributos(c.target);
        }
    }).observe(document.documentElement, {
        childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATRIBUTOS
    });

    // ---------- DIÁLOGOS DEL NAVEGADOR ----------
    ["alert", "confirm", "prompt"].forEach((nombre) => {
        const original = window[nombre].bind(window);
        window[nombre] = (mensaje, ...resto) => original(tLineas(mensaje), ...resto);
    });

    // ---------- SELECTOR CON BANDERA ----------
    let contadorBanderas = 0;
    function bandera(codigo) {
        if (codigo === "es") {
            return `<svg viewBox="0 0 30 20" class="w-5 h-[13px] rounded-sm shrink-0" aria-hidden="true">
                <rect width="30" height="20" fill="#AA151B"/><rect y="5" width="30" height="10" fill="#F1BF00"/></svg>`;
        }
        const id = `uk-${++contadorBanderas}`;
        return `<svg viewBox="0 0 60 30" class="w-5 h-[13px] rounded-sm shrink-0" aria-hidden="true">
            <clipPath id="${id}-a"><path d="M0,0 v30 h60 v-30 z"/></clipPath>
            <clipPath id="${id}-b"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath>
            <g clip-path="url(#${id}-a)">
                <path d="M0,0 v30 h60 v-30 z" fill="#012169"/>
                <path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/>
                <path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#${id}-b)" stroke="#C8102E" stroke-width="4"/>
                <path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/>
                <path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/>
            </g></svg>`;
    }

    // Cada hueco <span data-selector-idioma></span> se convierte en un botón que alterna ES <-> EN
    function pintarSelectores() {
        document.querySelectorAll("[data-selector-idioma]").forEach((hueco) => {
            hueco.innerHTML = `
                <button type="button" onclick="alternarIdioma()" title="Cambiar idioma" aria-label="Cambiar idioma"
                    class="flex items-center gap-1.5 font-mono text-[10px] font-semibold text-zinc-200 hover:text-matcha bg-panel border border-panelBorder px-2 py-1 rounded-full transition uppercase">
                    ${bandera(idioma)}<span translate="no">${idioma.toUpperCase()}</span>
                </button>`;
        });
    }

    function aplicarIdioma(nuevo) {
        if (!IDIOMAS.includes(nuevo)) return;
        idioma = nuevo;
        try { localStorage.setItem(CLAVE, nuevo); } catch (e) {}
        document.documentElement.lang = nuevo;
        pintarSelectores();
        procesarArbol(document.documentElement);
        // Aviso para lo que no vive en el DOM (gráficas, botón de Google...)
        window.dispatchEvent(new CustomEvent("nutri:idioma", { detail: { idioma: nuevo } }));
    }

    function alternarIdioma() {
        aplicarIdioma(idioma === "es" ? "en" : "es");
    }

    Object.assign(window, {
        t,
        idiomaActual: () => idioma,
        aplicarIdioma,
        alternarIdioma
    });

    document.addEventListener("DOMContentLoaded", () => {
        pintarSelectores();
        procesarArbol(document.documentElement);
    });
})();
