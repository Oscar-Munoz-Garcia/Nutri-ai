// Comidas del día: cada plan tiene su número de comidas con nombre (Desayuno, Pre-entreno, Cena...),
// el Diario agrupa los registros por esas comidas y el botón «+» añade alimentos por gramos a la comida que elijas,
// con sus macros en gramos y en % y una rueda de colores antes de confirmar.
// Usa API_BASE, el fetch con JWT, colorTema, planHoy y cargarResumenDiario de index.html; los estilos nx-* de dashboard360.js.
(function () {
    const esc = (t) => String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const tr = (texto) => (window.t ? window.t(texto) : texto);
    const r1 = (x) => Math.round(x * 10) / 10;
    const ingles = () => window.idiomaActual?.() === "en";

    // Mismo reparto que plan_service.COMIDAS_SUGERIDAS
    const SUGERIDAS = {
        1: ["Comida"],
        2: ["Comida", "Cena"],
        3: ["Desayuno", "Comida", "Cena"],
        4: ["Desayuno", "Comida", "Merienda", "Cena"],
        5: ["Desayuno", "Almuerzo", "Comida", "Merienda", "Cena"],
        6: ["Desayuno", "Almuerzo", "Comida", "Merienda", "Cena", "Recena"],
        7: ["Desayuno", "Almuerzo", "Comida", "Pre-entreno", "Post-entreno", "Cena", "Recena"],
        8: ["Desayuno", "Almuerzo", "Comida", "Merienda", "Pre-entreno", "Post-entreno", "Cena", "Recena"]
    };
    const sugeridas = (n) => SUGERIDAS[n].map(tr);

    const estilos = document.createElement("style");
    estilos.textContent = `
        .nx-fab-add { left: auto; right: 1.25rem; font-size: 1.9rem; font-weight: 300; }
        .ca-chip { border-radius: 9999px; padding: .3rem .75rem; font-size: .7rem; border: 1px solid var(--nx-border); background: var(--nx-surface-2); color: var(--nx-muted); }
        .ca-chip.ca-on { border-color: var(--nx-accent); color: var(--nx-text); background: color-mix(in srgb, var(--nx-accent) 18%, transparent); }
        .ca-resultado { width: 100%; text-align: left; padding: .5rem .75rem; border-radius: .85rem; background: var(--nx-surface-2); border: 1px solid var(--nx-border); }
        .ca-resultado:hover { border-color: var(--nx-accent); }
        .ca-barra { display: flex; height: 6px; border-radius: 9999px; overflow: hidden; background: var(--nx-border); }
        .ca-punto { width: .55rem; height: .55rem; border-radius: 9999px; display: inline-block; }
    `;
    document.head.appendChild(estilos);

    // ---------- EDITOR DE COMIDAS (formulario de planes, perfil y cuestionario de alta) ----------
    function pintarEditorComidas(id, comidas) {
        const cont = document.getElementById(id);
        if (!cont) return;
        const lista = comidas && comidas.length ? comidas : sugeridas(3);
        cont.innerHTML = `
            <label class="text-zinc-400 block mb-1 text-[10px]">Comidas al día</label>
            <div class="flex items-center gap-2">
                <select data-num-comidas onchange="cambiarNumeroComidas('${id}', this.value)" class="w-16 bg-canvas border border-panelBorder text-zinc-200 px-2 py-2 rounded focus:outline-none focus:border-matcha">
                    ${Object.keys(SUGERIDAS).map(n => `<option value="${n}" ${+n === lista.length ? "selected" : ""}>${n}</option>`).join("")}
                </select>
                <span class="text-zinc-500 text-[10px] leading-snug">Ponles el nombre que quieras, por ejemplo Pre-entreno.</span>
            </div>
            <div class="grid grid-cols-2 gap-2 mt-2">
                ${lista.map((c, i) => `
                    <input type="text" data-comida value="${esc(c)}" maxlength="30" required placeholder="Comida ${i + 1}"
                           class="w-full bg-canvas border border-panelBorder text-zinc-200 px-3 py-2 rounded focus:outline-none focus:border-matcha">`).join("")}
            </div>`;
    }

    function leerComidas(id) {
        const cont = document.getElementById(id);
        if (!cont || !cont.querySelector("[data-comida]")) return null;
        const comidas = [...cont.querySelectorAll("[data-comida]")].map(i => i.value.trim()).filter(Boolean);
        return comidas.length ? comidas : null;
    }

    // Si las comidas siguen siendo las sugeridas se cambian por las del nuevo número;
    // si se han personalizado se conservan y solo se añaden o quitan al final.
    function cambiarNumeroComidas(id, numero) {
        const n = parseInt(numero, 10);
        const cont = document.getElementById(id);
        const actuales = [...cont.querySelectorAll("[data-comida]")].map(i => i.value.trim());
        // Las sugeridas pueden estar guardadas en español aunque la interfaz esté en inglés
        const enEspanol = SUGERIDAS[actuales.length]?.join("|") === actuales.join("|");
        const traducidas = SUGERIDAS[actuales.length] && sugeridas(actuales.length).join("|") === actuales.join("|");
        let nuevas;
        if (enEspanol || traducidas) {
            nuevas = enEspanol ? [...SUGERIDAS[n]] : sugeridas(n);
        } else {
            nuevas = actuales.slice(0, n);
            for (const s of sugeridas(n)) if (nuevas.length < n && !nuevas.includes(s)) nuevas.push(s);
            while (nuevas.length < n) nuevas.push(`${tr("Comida")} ${nuevas.length + 1}`);
        }
        pintarEditorComidas(id, nuevas);
    }

    // ---------- DIARIO AGRUPADO POR COMIDAS ----------
    let ultimosRegistros = [];
    const igual = (a, b) => String(a || "").trim().toLowerCase() === String(b || "").trim().toLowerCase();

    function comidasDelDia() {
        return (typeof planHoy !== "undefined" && planHoy && planHoy.comidas) || [];
    }

    // Comida del plan que corresponde a una detectada por voz ("Desayuno" o, en inglés, "Breakfast")
    function comidaSugerida(detectada) {
        const comidas = comidasDelDia();
        if (detectada) {
            const encontrada = comidas.find(c => igual(c, detectada) || igual(tr(c), detectada));
            if (encontrada) return encontrada;
        }
        return siguienteComida();
    }

    // La comida que toca: la siguiente a la última que ya tiene algo registrado
    function siguienteComida() {
        const comidas = comidasDelDia();
        let ultima = -1;
        comidas.forEach((c, i) => { if (ultimosRegistros.some(r => igual(r.comida, c))) ultima = i; });
        return comidas[Math.min(ultima + 1, comidas.length - 1)] || null;
    }

    function pintarRegistrosPorComida(cont, registros, plan) {
        ultimosRegistros = registros;
        const comidas = (plan && plan.comidas) || [];
        const grupos = comidas.map(nombre => ({ nombre, enPlan: true, items: [] }));
        for (const r of registros) {
            let grupo = grupos.find(g => r.comida && igual(g.nombre, r.comida));
            if (!grupo) {
                grupo = grupos.find(g => !g.enPlan && igual(g.nombre, r.comida));
                if (!grupo) grupos.push(grupo = { nombre: r.comida || null, enPlan: false, items: [] });
            }
            grupo.items.push(r);
        }
        // Los grupos sin comida del plan (registros antiguos, recetas, escáner...) van al final
        grupos.sort((a, b) => (a.enPlan === b.enPlan ? 0 : a.enPlan ? -1 : 1) || (a.nombre === null) - (b.nombre === null));

        const item = (r) => `
            <div class="p-3 bg-canvas border border-panelBorder rounded-xl flex justify-between items-center font-mono text-[11px]">
                <div class="min-w-0">
                    <span class="text-zinc-200 font-semibold block truncate" translate="no">${esc(r.nombre)}</span>
                    ${r.gramos ? `<span class="text-zinc-400 text-[9px]" translate="no">${r1(r.gramos)} g · </span>` : ""}<span class="text-zinc-500 text-[9px]">🔥 ${r.calorias} kcal · P: ${r.proteinas}g · C: ${r.carbohidratos}g · G: ${r.grasas}g</span>
                </div>
                <button onclick="eliminarConsumoDiario(${r.id})" class="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition" title="Eliminar registro">
                    🗑️
                </button>
            </div>`;

        cont.innerHTML = (registros.length ? "" : '<p class="font-mono text-[11px] text-center text-zinc-500 py-1">Sin consumos registrados este día.</p>') +
            grupos.map(g => {
                const kcal = Math.round(g.items.reduce((s, r) => s + (r.calorias || 0), 0));
                return `
                <div class="space-y-1.5 pt-1">
                    <div class="flex justify-between items-center gap-2">
                        <span class="font-mono text-[10px] uppercase tracking-wider font-semibold ${g.enPlan ? "text-matcha" : "text-zinc-400"} truncate">${g.nombre === null ? "Sin comida asignada" : esc(g.nombre)}</span>
                        <span class="flex items-center gap-2 shrink-0">
                            <span class="font-mono text-[10px] text-zinc-500">${kcal} kcal</span>
                            ${g.enPlan ? `<button data-comida="${esc(g.nombre)}" onclick="abrirAnadirAlimentos(this.dataset.comida)" title="Añadir a esta comida" aria-label="Añadir a esta comida"
                                class="w-6 h-6 leading-none rounded-full border border-matcha/40 text-matcha hover:border-matcha text-sm">+</button>` : ""}
                        </span>
                    </div>
                    ${g.items.map(item).join("")}
                </div>`;
            }).join("");
    }

    // ---------- AÑADIR ALIMENTOS POR GRAMOS ----------
    // alimentos: [{ nombre, por100: { kcal, prot, carb, gras }, gramos, comida, propia, origen }]
    let hoja = null;
    let temporizadorBusqueda = null;
    let busquedaActual = 0;
    let graficoRueda = null;

    const MACROS = [
        { k: "prot", nombre: "Proteínas", corto: "P", color: () => colorMacro("--c-accent", "#49C6D4") },
        { k: "carb", nombre: "Carbohidratos", corto: "C", color: () => colorMacro("--c-carb", "#2F64B3") },
        { k: "gras", nombre: "Grasas", corto: "G", color: () => colorMacro("--c-fat", "#E0607E") }
    ];

    function colorMacro(variable, porDefecto) {
        try { return (typeof colorTema === "function" && colorTema(variable)) || porDefecto; } catch (e) { return porDefecto; }
    }

    function fechaDestino() {
        if (typeof window.fechaDiario === "function") return window.fechaDiario();
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    function macrosDe(a) {
        const f = (parseFloat(a.gramos) || 0) / 100;
        let kcal = a.por100.kcal;
        // En un alimento propio sin kcal se calculan con los macros
        if (!kcal) kcal = a.por100.prot * 4 + a.por100.carb * 4 + a.por100.gras * 9;
        return { kcal: kcal * f, prot: a.por100.prot * f, carb: a.por100.carb * f, gras: a.por100.gras * f };
    }

    // % de cada macro sobre el total de gramos de macros (0 C, 20 P, 20 G -> 0 %, 50 %, 50 %)
    function porcentajes(m) {
        const total = m.prot + m.carb + m.gras;
        return Object.fromEntries(MACROS.map(({ k }) => [k, total > 0 ? Math.round(m[k] / total * 100) : 0]));
    }

    function sumar(lista) {
        return lista.map(macrosDe).reduce((s, m) => ({ kcal: s.kcal + m.kcal, prot: s.prot + m.prot, carb: s.carb + m.carb, gras: s.gras + m.gras }),
            { kcal: 0, prot: 0, carb: 0, gras: 0 });
    }

    function abrirAnadirAlimentos(comida) {
        cerrarAnadirAlimentos();
        const comidas = comidasDelDia();
        hoja = { comida: (comida && comidas.find(c => igual(c, comida))) || siguienteComida(), alimentos: [], foco: null };

        const fecha = fechaDestino();
        const esHoy = typeof window.esDiarioHoy === "function" ? window.esDiarioHoy() : true;
        const locale = ingles() ? "en-GB" : "es-ES";
        const fechaTexto = new Date(`${fecha}T12:00:00`).toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" });

        const ov = document.createElement("div");
        ov.id = "ca-hoja";
        ov.className = "nx-overlay";
        ov.onclick = (e) => { if (e.target === ov) cerrarAnadirAlimentos(); };
        ov.innerHTML = `
            <div class="nx-sheet space-y-4">
                <div class="flex justify-between items-center">
                    <div>
                        <h3 class="font-display font-semibold text-base">Añadir alimentos</h3>
                        <span class="text-[11px] ${esHoy ? "nx-muted" : "text-amberAccent font-semibold"}" translate="no">📅 ${esc(fechaTexto)}</span>
                    </div>
                    <button class="nx-muted text-lg" onclick="cerrarAnadirAlimentos()" aria-label="Cerrar">✕</button>
                </div>
                ${comidas.length ? `
                <div class="space-y-1.5">
                    <span class="text-[10px] uppercase tracking-widest nx-muted">Añadir a</span>
                    <div id="ca-comidas" class="flex flex-wrap gap-1.5"></div>
                </div>` : ""}
                <div class="space-y-1.5">
                    <input id="ca-buscar" type="search" autocomplete="off" class="nx-input" placeholder="Busca un alimento: arroz, pollo, tomate…" oninput="buscarAlimentoDiario(this.value)">
                    <div id="ca-resultados" class="space-y-1.5"></div>
                </div>
                <div id="ca-lista" class="space-y-2"></div>
                <div id="ca-resumen"></div>
                <p id="ca-error" class="text-[11px] text-rose-400 text-center hidden"></p>
                <button id="ca-guardar" class="nx-btn nx-btn-primary w-full !py-3" onclick="guardarAlimentosDiario()" disabled>Añadir</button>
            </div>`;
        document.body.appendChild(ov);
        pintarChipsComida();
        pintarListaAlimentos();
        document.getElementById("ca-buscar").focus();
    }

    function cerrarAnadirAlimentos() {
        if (graficoRueda) { graficoRueda.destroy(); graficoRueda = null; }
        document.getElementById("ca-hoja")?.remove();
        hoja = null;
    }

    function opcionesComida(seleccionada) {
        return comidasDelDia().map(c => `<option value="${esc(c)}" ${igual(c, seleccionada) ? "selected" : ""}>${esc(c)}</option>`).join("");
    }

    function pintarChipsComida() {
        const cont = document.getElementById("ca-comidas");
        if (!cont || !hoja) return;
        cont.innerHTML = comidasDelDia().map(c =>
            `<button type="button" data-comida="${esc(c)}" onclick="elegirComidaHoja(this.dataset.comida)" class="ca-chip${igual(c, hoja.comida) ? " ca-on" : ""}">${esc(c)}</button>`
        ).join("");
    }

    // Cambia la comida de la hoja y la de los alimentos a los que no se les ha elegido otra a mano
    function elegirComidaHoja(comida) {
        hoja.comida = comida;
        hoja.alimentos.forEach(a => { if (!a.comidaElegida) a.comida = comida; });
        pintarChipsComida();
        pintarListaAlimentos();
    }

    function buscarAlimentoDiario(texto) {
        clearTimeout(temporizadorBusqueda);
        const cont = document.getElementById("ca-resultados");
        const q = texto.trim();
        if (!q) { cont.innerHTML = ""; return; }
        temporizadorBusqueda = setTimeout(async () => {
            const n = ++busquedaActual;
            let resultados = [];
            try {
                const res = await fetch(`${API_BASE}/alimentos/buscar?q=${encodeURIComponent(q)}`);
                if (res.ok) resultados = await res.json();
            } catch (e) { /* se ofrece igualmente crearlo a mano */ }
            if (n !== busquedaActual || !hoja) return;
            hoja.resultados = resultados;
            cont.innerHTML = resultados.map((a, i) => `
                <button type="button" class="ca-resultado" onclick="elegirAlimentoDiario(${i})">
                    <span class="block text-xs font-semibold" translate="no">${esc(ingles() && a.nombre_en ? a.nombre_en : a.nombre)} ${a.origen === "despensa" ? '<span class="nx-muted font-normal">· 📦</span>' : ""}</span>
                    <span class="text-[10px] nx-muted">Por 100 g: ${Math.round(a.calorias_100g)} kcal · P ${r1(a.proteinas_100g)}g · C ${r1(a.carbohidratos_100g)}g · G ${r1(a.grasas_100g)}g</span>
                </button>`).join("") + `
                <button type="button" class="ca-resultado text-xs" data-nombre="${esc(q)}" onclick="anadirAlimentoPropio(this.dataset.nombre)">
                    ＋ <span>Crear a mano:</span> <strong translate="no">${esc(q)}</strong>
                </button>`;
        }, 250);
    }

    function nuevoAlimento(datos) {
        hoja.alimentos.push({ gramos: 100, comida: hoja.comida, comidaElegida: false, ...datos });
        document.getElementById("ca-buscar").value = "";
        document.getElementById("ca-resultados").innerHTML = "";
        hoja.foco = null;
        pintarListaAlimentos();
        // Lo normal es cambiar los gramos nada más añadirlo
        const campos = document.querySelectorAll("#ca-lista [data-gramos]");
        campos[campos.length - 1]?.select();
    }

    function elegirAlimentoDiario(i) {
        const a = hoja?.resultados?.[i];
        if (!a) return;
        nuevoAlimento({
            nombre: ingles() && a.nombre_en ? a.nombre_en : a.nombre, origen: a.origen, propia: false,
            por100: { kcal: a.calorias_100g, prot: a.proteinas_100g, carb: a.carbohidratos_100g, gras: a.grasas_100g }
        });
    }

    function anadirAlimentoPropio(nombre) {
        nuevoAlimento({ nombre, origen: "propio", propia: true, por100: { kcal: 0, prot: 0, carb: 0, gras: 0 } });
    }

    function lineaMacros(m) {
        const pct = porcentajes(m);
        return `
            <div class="grid grid-cols-4 gap-1 text-center text-[10px]">
                <div><span class="block font-bold text-xs">${Math.round(m.kcal)}</span><span class="nx-muted">kcal</span></div>
                ${MACROS.map(x => `<div><span class="block font-bold text-xs" style="color:${x.color()}">${r1(m[x.k])} g</span><span class="nx-muted">${x.corto} · ${pct[x.k]}%</span></div>`).join("")}
            </div>
            <div class="ca-barra">${MACROS.map(x => `<div style="width:${pct[x.k]}%; background:${x.color()}"></div>`).join("")}</div>`;
    }

    function pintarListaAlimentos() {
        const lista = document.getElementById("ca-lista");
        if (!lista || !hoja) return;
        const comidas = comidasDelDia();
        const campo100 = (i, k, v, etiqueta) => `<label class="text-[9px] nx-muted text-center">${etiqueta}
            <input type="number" inputmode="decimal" step="0.1" min="0" value="${v || ""}" oninput="cambiarPor100(${i}, '${k}', this.value)" class="nx-input text-center !px-1"></label>`;

        lista.innerHTML = hoja.alimentos.map((a, i) => `
            <div class="nx-stat space-y-2${hoja.foco === i ? " ring-1 ring-[color:var(--nx-accent)]" : ""}">
                <div class="flex items-center gap-2">
                    ${a.propia
                        ? `<input value="${esc(a.nombre)}" maxlength="80" oninput="cambiarNombreAlimento(${i}, this.value)" class="nx-input font-semibold flex-1" translate="no">`
                        : `<button type="button" onclick="enfocarAlimento(${i})" title="Ver en la rueda" class="flex-1 min-w-0 text-left text-sm font-semibold truncate" translate="no">${esc(a.nombre)}</button>`}
                    <button type="button" class="nx-muted text-sm px-1" onclick="quitarAlimentoDiario(${i})" aria-label="Quitar">✕</button>
                </div>
                ${a.propia ? `
                <div class="space-y-1">
                    <span class="text-[10px] nx-muted">Valores por 100 g</span>
                    <div class="grid grid-cols-4 gap-1.5">
                        ${campo100(i, "kcal", a.por100.kcal, "kcal")}${campo100(i, "prot", a.por100.prot, "Prot")}${campo100(i, "carb", a.por100.carb, "Carbs")}${campo100(i, "gras", a.por100.gras, "Grasas")}
                    </div>
                </div>` : ""}
                <div class="flex items-center gap-2">
                    <label class="flex items-center gap-1 shrink-0">
                        <input type="number" inputmode="decimal" data-gramos min="1" step="1" value="${a.gramos}" oninput="cambiarGramosAlimento(${i}, this.value)" class="nx-input text-center font-semibold" style="width: 5.5rem">
                        <span class="text-xs nx-muted">g</span>
                    </label>
                    ${comidas.length ? `<select onchange="cambiarComidaAlimento(${i}, this.value)" class="nx-input flex-1 min-w-0" aria-label="Elegir comida">${opcionesComida(a.comida)}</select>` : ""}
                </div>
                <div id="ca-macros-${i}" class="space-y-1.5">${lineaMacros(macrosDe(a))}</div>
            </div>`).join("");
        actualizarResumen();
    }

    function refrescarAlimento(i) {
        const cont = document.getElementById(`ca-macros-${i}`);
        if (cont) cont.innerHTML = lineaMacros(macrosDe(hoja.alimentos[i]));
        actualizarResumen();
    }

    function cambiarGramosAlimento(i, valor) { hoja.alimentos[i].gramos = parseFloat(valor) || 0; refrescarAlimento(i); }
    function cambiarPor100(i, k, valor) { hoja.alimentos[i].por100[k] = parseFloat(valor) || 0; refrescarAlimento(i); }
    function cambiarNombreAlimento(i, valor) { hoja.alimentos[i].nombre = valor; actualizarResumen(); }
    function cambiarComidaAlimento(i, valor) { hoja.alimentos[i].comida = valor; hoja.alimentos[i].comidaElegida = true; }

    function quitarAlimentoDiario(i) {
        hoja.alimentos.splice(i, 1);
        hoja.foco = null;
        pintarListaAlimentos();
    }

    function enfocarAlimento(i) {
        hoja.foco = hoja.foco === i ? null : i;
        pintarListaAlimentos();
    }

    function actualizarResumen() {
        const cont = document.getElementById("ca-resumen");
        const btn = document.getElementById("ca-guardar");
        if (!cont || !hoja) return;
        const n = hoja.alimentos.length;
        const validos = n > 0 && hoja.alimentos.every(a => a.gramos > 0 && a.nombre.trim());
        btn.disabled = !validos;
        btn.textContent = n === 1 ? tr("Añadir 1 alimento") : n ? tr(`Añadir ${n} alimentos`) : tr("Añadir");
        if (!n) {
            if (graficoRueda) { graficoRueda.destroy(); graficoRueda = null; }
            cont.innerHTML = '<p class="text-[11px] nx-muted text-center">Busca y añade cada alimento con sus gramos, por ejemplo 200 g de arroz y 150 g de pollo.</p>';
            return;
        }

        const enFoco = hoja.foco !== null && hoja.alimentos[hoja.foco];
        const m = enFoco ? macrosDe(enFoco) : sumar(hoja.alimentos);
        const pct = porcentajes(m);
        if (!document.getElementById("ca-rueda")) {
            cont.innerHTML = `
                <div class="nx-stat space-y-3">
                    <div class="flex justify-between items-center gap-2">
                        <span id="ca-resumen-titulo" class="text-xs font-semibold truncate"></span>
                        <button id="ca-ver-total" type="button" class="ca-chip hidden">Ver total</button>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="relative w-32 h-32 shrink-0">
                            <canvas id="ca-rueda"></canvas>
                            <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                                <span id="ca-rueda-kcal" class="font-display font-bold text-xl leading-none"></span>
                                <span class="text-[10px] nx-muted">kcal</span>
                            </div>
                        </div>
                        <div id="ca-leyenda" class="flex-1 space-y-2 text-xs"></div>
                    </div>
                    <p class="text-[10px] nx-muted">% de cada macro sobre el total de gramos de macros.</p>
                </div>`;
            document.getElementById("ca-ver-total").onclick = () => enfocarAlimento(hoja.foco);
        }
        const titulo = document.getElementById("ca-resumen-titulo");
        titulo.textContent = enFoco ? enFoco.nombre : (n === 1 ? hoja.alimentos[0].nombre : tr("Total"));
        titulo.translate = !enFoco && n > 1;
        document.getElementById("ca-ver-total").classList.toggle("hidden", !enFoco || n === 1);
        document.getElementById("ca-rueda-kcal").textContent = Math.round(m.kcal);
        document.getElementById("ca-leyenda").innerHTML = MACROS.map(x => `
            <div class="flex items-center gap-2">
                <span class="ca-punto" style="background:${x.color()}"></span>
                <span class="flex-1">${x.nombre}</span>
                <strong class="whitespace-nowrap">${r1(m[x.k])} g</strong>
                <span class="nx-muted w-10 text-right">${pct[x.k]}%</span>
            </div>`).join("");
        pintarRueda(m);
    }

    function pintarRueda(m) {
        const canvas = document.getElementById("ca-rueda");
        if (!canvas || !window.Chart) return;
        const hayDatos = m.prot + m.carb + m.gras > 0;
        const datos = hayDatos ? MACROS.map(x => r1(m[x.k])) : [1];
        const colores = hayDatos ? MACROS.map(x => x.color()) : [colorMacro("--c-border", "#888")];
        const etiquetas = hayDatos ? MACROS.map(x => tr(x.nombre)) : [""];
        if (graficoRueda && graficoRueda.canvas === canvas) {
            Object.assign(graficoRueda.data, { labels: etiquetas });
            Object.assign(graficoRueda.data.datasets[0], { data: datos, backgroundColor: colores });
            graficoRueda.update();
            return;
        }
        graficoRueda?.destroy();
        graficoRueda = new Chart(canvas.getContext("2d"), {
            type: "doughnut",
            data: { labels: etiquetas, datasets: [{ data: datos, backgroundColor: colores, borderWidth: 0, hoverOffset: 4 }] },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: "70%", animation: { duration: 250 },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: hayDatos, callbacks: { label: (c) => ` ${c.label}: ${c.raw} g` } }
                }
            }
        });
    }

    async function guardarAlimentosDiario() {
        const btn = document.getElementById("ca-guardar");
        const error = document.getElementById("ca-error");
        btn.disabled = true;
        error.classList.add("hidden");
        const fecha = fechaDestino();
        // Se van quitando de la hoja según se guardan: si falla uno, reintentar no duplica los anteriores
        while (hoja && hoja.alimentos.length) {
            const a = hoja.alimentos[0];
            const m = macrosDe(a);
            try {
                const res = await fetch(`${API_BASE}/diario/consumo?fecha=${encodeURIComponent(fecha)}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        nombre: a.nombre.trim(), calorias: r1(m.kcal), proteinas: r1(m.prot), carbohidratos: r1(m.carb),
                        grasas: r1(m.gras), gramos: r1(a.gramos), comida: a.comida || null
                    })
                });
                if (!res.ok) throw new Error(res.status);
            } catch (e) {
                error.textContent = tr("No se pudo guardar. Revisa la conexión y vuelve a intentarlo.");
                error.classList.remove("hidden");
                hoja.foco = null;
                pintarListaAlimentos();
                if (typeof cargarResumenDiario === "function") cargarResumenDiario();
                return;
            }
            hoja.alimentos.shift();
        }
        cerrarAnadirAlimentos();
        if (typeof cargarResumenDiario === "function") cargarResumenDiario();
    }

    function crearFabAnadir() {
        if (document.getElementById("ca-fab")) return;
        const fab = document.createElement("button");
        fab.id = "ca-fab";
        fab.className = "nx-fab nx-fab-add";
        fab.title = "Añadir alimentos";
        fab.setAttribute("aria-label", "Añadir alimentos");
        fab.textContent = "+";
        fab.onclick = () => abrirAnadirAlimentos();
        document.body.appendChild(fab);
    }

    // La rueda usa los colores del tema
    window.addEventListener("nutri:tema", () => { if (hoja) { graficoRueda?.destroy(); graficoRueda = null; pintarListaAlimentos(); } });

    Object.assign(window, {
        pintarEditorComidas, leerComidas, cambiarNumeroComidas, pintarRegistrosPorComida, comidasDelDia, comidaSugerida,
        abrirAnadirAlimentos, cerrarAnadirAlimentos, elegirComidaHoja, buscarAlimentoDiario, elegirAlimentoDiario,
        anadirAlimentoPropio, cambiarGramosAlimento, cambiarPor100, cambiarNombreAlimento, cambiarComidaAlimento,
        quitarAlimentoDiario, enfocarAlimento, guardarAlimentosDiario
    });

    crearFabAnadir();
})();
