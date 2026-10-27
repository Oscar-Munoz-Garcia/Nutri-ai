// Dashboard 360°: calendario de constancia, registro rápido por voz y modo cocina.
// Usa API_BASE y el wrapper de fetch con JWT definidos en index.html.
// Los colores salen de variables CSS (--color-1/2/3, --nx-*) para que el tema claro/oscuro las pueda redefinir.
(function () {
    const esc = (t) => String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    const estilos = document.createElement("style");
    estilos.textContent = `
        :root {
            --nx-accent: var(--color-1, #49C6D4);
            --nx-accent-2: var(--color-2, #4981D4);
            --nx-accent-3: var(--color-3, #5749D4);
            --nx-surface: var(--surface, #121418);
            --nx-surface-2: var(--surface-2, #0B0C0E);
            --nx-border: var(--border, #1E222A);
            --nx-text: var(--text, #F4F4F5);
            --nx-muted: var(--text-muted, #A1A1AA);
            --nx-heat-0: var(--heat-0, rgba(161, 161, 170, 0.18));
            --nx-heat-1: var(--heat-1, rgba(161, 161, 170, 0.45));
            --nx-heat-2: var(--heat-2, #2E8B57);
            --nx-heat-3: var(--heat-3, #14532D);
        }
        .nx-card { background: var(--nx-surface); border: 1px solid var(--nx-border); border-radius: 1.25rem; padding: 1.25rem; color: var(--nx-text); }
        .nx-muted { color: var(--nx-muted); }
        .nx-heat { display: grid; grid-auto-flow: column; grid-template-rows: repeat(7, 1fr); gap: 3px; overflow-x: auto; padding-bottom: 4px; }
        .nx-cell { width: 12px; height: 12px; border-radius: 3px; background: var(--nx-heat-0); }
        .nx-cell[data-n="1"] { background: var(--nx-heat-1); }
        .nx-cell[data-n="2"] { background: var(--nx-heat-2); }
        .nx-cell[data-n="3"] { background: var(--nx-heat-3); }
        .nx-cell.nx-hoy { outline: 2px solid var(--nx-accent); outline-offset: 1px; }
        .nx-cell.nx-futuro { visibility: hidden; }
        .nx-stat { background: var(--nx-surface-2); border: 1px solid var(--nx-border); border-radius: 1rem; padding: .6rem .75rem; }
        .nx-btn { border-radius: 9999px; padding: .55rem 1rem; font-weight: 600; font-size: .75rem; transition: opacity .2s, transform .1s; }
        .nx-btn:active { transform: scale(.97); }
        .nx-btn:disabled { opacity: .5; }
        .nx-btn-primary { background: linear-gradient(135deg, var(--nx-accent), var(--nx-accent-2)); color: #fff; }
        .nx-btn-ghost { background: var(--nx-surface-2); border: 1px solid var(--nx-border); color: var(--nx-text); }
        .nx-input { width: 100%; background: var(--nx-surface-2); border: 1px solid var(--nx-border); color: var(--nx-text); border-radius: .85rem; padding: .5rem .75rem; font-size: .75rem; }
        .nx-input:focus { outline: none; border-color: var(--nx-accent); }
        .nx-fab { position: fixed; right: 1.25rem; bottom: 1.5rem; z-index: 45; width: 3.5rem; height: 3.5rem; border-radius: 9999px; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;
                  background: linear-gradient(135deg, var(--nx-accent), var(--nx-accent-3)); color: #fff; box-shadow: 0 10px 25px rgba(0,0,0,.35); }
        .nx-overlay { position: fixed; inset: 0; z-index: 55; background: rgba(0,0,0,.55); backdrop-filter: blur(6px); display: flex; align-items: flex-end; justify-content: center; }
        .nx-sheet { width: 100%; max-width: 28rem; max-height: 90vh; overflow-y: auto; background: var(--nx-surface); color: var(--nx-text); border-radius: 1.5rem 1.5rem 0 0; padding: 1.25rem; border: 1px solid var(--nx-border); }
        @media (min-width: 640px) { .nx-overlay { align-items: center; } .nx-sheet { border-radius: 1.5rem; } }
        .nx-mic { width: 4.5rem; height: 4.5rem; border-radius: 9999px; font-size: 1.8rem; background: var(--nx-surface-2); border: 2px solid var(--nx-accent); color: var(--nx-accent); }
        .nx-mic.nx-on { background: var(--nx-accent); color: #fff; animation: nx-pulse 1.2s infinite; }
        @keyframes nx-pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(73,198,212,.55); } 50% { box-shadow: 0 0 0 14px rgba(73,198,212,0); } }
        .nx-cook { position: fixed; inset: 0; z-index: 60; background: var(--nx-surface-2); color: var(--nx-text); overflow-y: auto; }
        .nx-step { border-radius: 1rem; padding: 1rem; border: 1px solid var(--nx-border); background: var(--nx-surface); opacity: .55; }
        .nx-step.nx-actual { opacity: 1; border-color: var(--nx-accent); }
        .nx-step.nx-hecho { opacity: .35; text-decoration: line-through; }
        .nx-check { display: flex; gap: .75rem; align-items: center; padding: .6rem .75rem; border-radius: .85rem; background: var(--nx-surface); border: 1px solid var(--nx-border); cursor: pointer; }
        .nx-check input { width: 1.1rem; height: 1.1rem; accent-color: var(--nx-accent); }
        .nx-check.nx-ok span { text-decoration: line-through; color: var(--nx-muted); }
        .nx-timer { display: flex; justify-content: space-between; align-items: center; gap: .5rem; padding: .6rem .9rem; border-radius: 9999px; background: var(--nx-surface); border: 1px solid var(--nx-border); }
        .nx-timer.nx-fin { border-color: var(--nx-accent); animation: nx-pulse 1s infinite; }
    `;
    document.head.appendChild(estilos);

    // ---------- CALENDARIO DE CONSTANCIA ----------
    async function cargarRacha() {
        const cont = document.getElementById("dash-racha");
        if (!cont) return;
        try {
            const res = await fetch(`${API_BASE}/diario/racha?dias=112`);
            if (!res.ok) throw new Error(res.status);
            const data = await res.json();
            const hoy = data.hasta;
            const celdas = data.dias.map(d => {
                const titulo = `${d.fecha}: ${d.calorias} kcal · ${d.proteinas} g prot` +
                    (d.nivel === 3 ? " ✓ metas cumplidas" : d.nivel === 0 ? " · sin registros" : "");
                return `<div class="nx-cell${d.fecha === hoy ? " nx-hoy" : ""}" data-n="${d.nivel}" title="${esc(titulo)}"></div>`;
            });
            // Rellenar hasta el domingo para cerrar la última columna
            const resto = (7 - (data.dias.length % 7)) % 7;
            for (let i = 0; i < resto; i++) celdas.push('<div class="nx-cell nx-futuro"></div>');

            cont.innerHTML = `
                <div class="nx-card space-y-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="text-[10px] uppercase tracking-widest nx-muted">Calendario de constancia</span>
                            <h2 class="font-display font-semibold text-lg">🔥 ${data.racha_actual} ${data.racha_actual === 1 ? "día" : "días"} de racha</h2>
                        </div>
                        <span class="text-[10px] nx-muted text-right">Meta: ${Math.round(data.meta_calorias)} kcal ±10%<br>y ≥ ${Math.round(data.meta_proteinas * 0.9)} g proteína</span>
                    </div>
                    <div class="nx-heat">${celdas.join("")}</div>
                    <div class="flex items-center justify-end gap-1.5 text-[10px] nx-muted">
                        <span>Sin datos</span>
                        <div class="nx-cell" data-n="0"></div><div class="nx-cell" data-n="1"></div>
                        <div class="nx-cell" data-n="2"></div><div class="nx-cell" data-n="3"></div>
                        <span>Ambas metas</span>
                    </div>
                    <div class="grid grid-cols-3 gap-2 text-center">
                        <div class="nx-stat"><span class="block text-lg font-bold">${data.mejor_racha}</span><span class="text-[10px] nx-muted">Mejor racha</span></div>
                        <div class="nx-stat"><span class="block text-lg font-bold">${data.dias_cumplidos}</span><span class="text-[10px] nx-muted">Días cumplidos</span></div>
                        <div class="nx-stat"><span class="block text-lg font-bold">${data.dias_registrados ? Math.round(data.dias_cumplidos / data.dias_registrados * 100) : 0}%</span><span class="text-[10px] nx-muted">Cumplimiento</span></div>
                    </div>
                </div>`;
        } catch (e) {
            console.error("Error cargando racha", e);
            cont.innerHTML = "";
        }
    }

    // ---------- REGISTRO RÁPIDO POR VOZ ----------
    const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;
    let reconocedor = null;
    let itemsPendientes = [];

    function abrirRegistroRapido() {
        cerrar("nx-quick");
        const ov = document.createElement("div");
        ov.id = "nx-quick";
        ov.className = "nx-overlay";
        ov.onclick = (e) => { if (e.target === ov) cerrarRegistroRapido(); };
        ov.innerHTML = `
            <div class="nx-sheet space-y-4">
                <div class="flex justify-between items-center">
                    <h3 class="font-display font-semibold text-base">Registro rápido</h3>
                    <button class="nx-muted text-lg" onclick="cerrarRegistroRapido()" aria-label="Cerrar">✕</button>
                </div>
                <div class="flex flex-col items-center gap-2">
                    <button id="nx-mic" class="nx-mic" ${Reconocimiento ? "" : "disabled"} onclick="alternarDictado()" aria-label="Dictar">🎙</button>
                    <span id="nx-mic-estado" class="text-[11px] nx-muted text-center">
                        ${Reconocimiento ? "Pulsa y dicta, por ejemplo: «Desayuno: 3 huevos cocidos y 80g de avena»" : "Tu navegador no admite dictado por voz; escríbelo abajo."}
                    </span>
                </div>
                <textarea id="nx-texto" rows="2" class="nx-input" placeholder="Desayuno: 3 huevos cocidos y 80g de avena"></textarea>
                <button id="nx-interpretar" class="nx-btn nx-btn-primary w-full" onclick="interpretarRegistroRapido()">Calcular macros</button>
                <div id="nx-preview" class="space-y-2"></div>
            </div>`;
        document.body.appendChild(ov);
        if (Reconocimiento) alternarDictado();
    }

    function cerrarRegistroRapido() {
        if (reconocedor) { reconocedor.onend = null; reconocedor.stop(); reconocedor = null; }
        cerrar("nx-quick");
    }

    function alternarDictado() {
        const mic = document.getElementById("nx-mic");
        const estado = document.getElementById("nx-mic-estado");
        if (reconocedor) { reconocedor.stop(); return; }

        reconocedor = new Reconocimiento();
        reconocedor.lang = "es-ES";
        reconocedor.interimResults = true;
        reconocedor.continuous = false;
        let textoFinal = "";

        reconocedor.onresult = (ev) => {
            let provisional = "";
            for (let i = ev.resultIndex; i < ev.results.length; i++) {
                const r = ev.results[i];
                if (r.isFinal) textoFinal += r[0].transcript;
                else provisional += r[0].transcript;
            }
            document.getElementById("nx-texto").value = (textoFinal + provisional).trim();
        };
        reconocedor.onerror = (ev) => {
            estado.textContent = ev.error === "not-allowed" ? "Permiso de micrófono denegado." : "No te he entendido, prueba otra vez.";
        };
        reconocedor.onend = () => {
            mic?.classList.remove("nx-on");
            reconocedor = null;
            if (textoFinal.trim()) {
                estado.textContent = "Revisa el texto o pulsa el micro para repetir.";
                interpretarRegistroRapido();
            }
        };
        mic.classList.add("nx-on");
        estado.textContent = "Escuchando…";
        reconocedor.start();
    }

    async function interpretarRegistroRapido() {
        const texto = document.getElementById("nx-texto").value.trim();
        const btn = document.getElementById("nx-interpretar");
        const preview = document.getElementById("nx-preview");
        if (!texto) return;
        btn.disabled = true;
        btn.textContent = "Calculando…";
        try {
            const res = await fetch(`${API_BASE}/diario/interpretar`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ texto })
            });
            if (!res.ok) throw new Error(res.status);
            const data = await res.json();
            itemsPendientes = data.items;
            renderizarPreview(data.avisos);
        } catch (e) {
            preview.innerHTML = '<p class="text-[11px] text-rose-400 text-center">No se pudo interpretar el texto.</p>';
        } finally {
            btn.disabled = false;
            btn.textContent = "Calcular macros";
        }
    }

    function renderizarPreview(avisos = []) {
        const preview = document.getElementById("nx-preview");
        const origen = { despensa: "📦 despensa", ia: "✨ estimado IA", sin_estimar: "⚠ rellena a mano" };
        const campo = (i, k, v) => `<input type="number" step="0.1" min="0" value="${v}" data-i="${i}" data-k="${k}" class="nx-input text-center !px-1" oninput="editarItemRapido(this)">`;
        preview.innerHTML = `
            ${avisos.map(a => `<p class="text-[10px] nx-muted text-center">${esc(a)}</p>`).join("")}
            ${itemsPendientes.map((it, i) => `
                <div class="nx-stat space-y-2">
                    <div class="flex justify-between items-center gap-2">
                        <input value="${esc(it.nombre)}" data-i="${i}" data-k="nombre" class="nx-input font-semibold" oninput="editarItemRapido(this)">
                        <button class="nx-muted text-sm px-1" onclick="quitarItemRapido(${i})" aria-label="Quitar">✕</button>
                    </div>
                    <div class="grid grid-cols-4 gap-1.5 text-[9px] nx-muted text-center">
                        <label>kcal${campo(i, "calorias", it.calorias)}</label>
                        <label>Prot${campo(i, "proteinas", it.proteinas)}</label>
                        <label>Carbs${campo(i, "carbohidratos", it.carbohidratos)}</label>
                        <label>Grasas${campo(i, "grasas", it.grasas)}</label>
                    </div>
                    <span class="text-[9px] nx-muted">${origen[it.origen] || ""}</span>
                </div>`).join("")}
            ${itemsPendientes.length ? `<button id="nx-guardar" class="nx-btn nx-btn-primary w-full" onclick="guardarRegistroRapido()">Guardar ${itemsPendientes.length} en el diario</button>` : ""}`;
    }

    function editarItemRapido(input) {
        const it = itemsPendientes[+input.dataset.i];
        it[input.dataset.k] = input.dataset.k === "nombre" ? input.value : (parseFloat(input.value) || 0);
    }

    function quitarItemRapido(i) {
        itemsPendientes.splice(i, 1);
        renderizarPreview();
    }

    async function guardarRegistroRapido() {
        const btn = document.getElementById("nx-guardar");
        btn.disabled = true;
        try {
            for (const it of itemsPendientes) {
                const res = await fetch(`${API_BASE}/diario/consumo`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        nombre: it.nombre, calorias: it.calorias, proteinas: it.proteinas,
                        carbohidratos: it.carbohidratos, grasas: it.grasas
                    })
                });
                if (!res.ok) throw new Error(res.status);
            }
            cerrarRegistroRapido();
            if (typeof cargarResumenDiario === "function") cargarResumenDiario();
        } catch (e) {
            btn.disabled = false;
            btn.textContent = "Error al guardar, reintentar";
        }
    }

    // ---------- MODO COCINA ----------
    let cocina = null; // { receta, pasos, actual, temporizadores, wakeLock }

    function extraerPasos(receta) {
        if (receta.pasos && receta.pasos.length) return receta.pasos;
        return (receta.descripcion || "")
            .split(/\n+|(?<=\.)\s+/)
            .map(p => p.trim())
            .filter(Boolean);
    }

    function minutosDePaso(texto) {
        const m = String(texto).match(/(\d+(?:[.,]\d+)?)\s*(?:min|minutos?)\b/i);
        return m ? parseFloat(m[1].replace(",", ".")) : null;
    }

    async function abrirModoCocina(recetaId) {
        let receta;
        try {
            const res = await fetch(`${API_BASE}/recetas`);
            receta = (await res.json()).find(r => String(r.id) === String(recetaId));
        } catch (e) { /* se informa abajo */ }
        if (!receta) { alert("No se encontró la receta."); return; }

        cocina = { receta, pasos: extraerPasos(receta), actual: 0, temporizadores: [], wakeLock: null, tick: null };
        const ov = document.createElement("div");
        ov.id = "nx-cook";
        ov.className = "nx-cook";
        document.body.appendChild(ov);
        renderizarCocina();

        try { await ov.requestFullscreen?.(); } catch (e) { /* algunos móviles no lo permiten */ }
        try { cocina.wakeLock = await navigator.wakeLock?.request("screen"); } catch (e) { /* opcional */ }
        cocina.tick = setInterval(actualizarTemporizadores, 1000);
    }

    function cerrarModoCocina() {
        if (!cocina) return;
        clearInterval(cocina.tick);
        cocina.wakeLock?.release?.();
        if (document.fullscreenElement) document.exitFullscreen?.();
        cocina = null;
        cerrar("nx-cook");
    }

    function renderizarCocina() {
        const ov = document.getElementById("nx-cook");
        if (!ov || !cocina) return;
        const { receta, pasos, actual } = cocina;
        const ingredientes = receta.ingredientes || [];
        const completados = cocina.checks || (cocina.checks = new Set());

        ov.innerHTML = `
            <div class="max-w-2xl mx-auto p-5 space-y-6 pb-32">
                <div class="flex justify-between items-start gap-3">
                    <div>
                        <span class="text-[10px] uppercase tracking-widest nx-muted">Modo cocina</span>
                        <h2 class="font-display font-bold text-2xl">${esc(receta.nombre)}</h2>
                        <span class="text-xs nx-muted">⏱ ${receta.tiempo_preparacion_min || "?"} min · ${Math.round(receta.calorias_totales)} kcal</span>
                    </div>
                    <button class="nx-btn nx-btn-ghost" onclick="cerrarModoCocina()">Salir ✕</button>
                </div>

                <section class="space-y-2">
                    <h3 class="text-xs uppercase tracking-widest nx-muted">Ingredientes ${ingredientes.length ? `(${completados.size}/${ingredientes.length})` : ""}</h3>
                    ${ingredientes.length ? ingredientes.map((ing, i) => `
                        <label class="nx-check${completados.has(i) ? " nx-ok" : ""}">
                            <input type="checkbox" ${completados.has(i) ? "checked" : ""} onchange="marcarIngrediente(${i})">
                            <span class="text-sm">${esc(ing.nombre)} <span class="nx-muted">· ${ing.cantidad_gramos} g</span></span>
                        </label>`).join("") : '<p class="text-xs nx-muted">Esta receta no tiene ingredientes detallados.</p>'}
                </section>

                <section class="space-y-2">
                    <h3 class="text-xs uppercase tracking-widest nx-muted">Pasos</h3>
                    ${pasos.length ? pasos.map((p, i) => {
                        const min = minutosDePaso(p);
                        return `
                        <div class="nx-step${i === actual ? " nx-actual" : i < actual ? " nx-hecho" : ""}" onclick="irAPaso(${i})">
                            <div class="flex gap-3">
                                <span class="font-display font-bold" style="color: var(--nx-accent)">${i + 1}</span>
                                <p class="text-base leading-relaxed flex-1">${esc(p)}</p>
                            </div>
                            ${min ? `<button class="nx-btn nx-btn-ghost mt-3 text-[11px]" onclick="event.stopPropagation(); iniciarTemporizador(${min * 60}, 'Paso ${i + 1}')">⏱ Temporizador ${min} min</button>` : ""}
                        </div>`;
                    }).join("") : '<p class="text-xs nx-muted">Esta receta no tiene pasos. Añádelos al crearla para usar el modo cocina.</p>'}
                </section>

                <section class="space-y-2">
                    <h3 class="text-xs uppercase tracking-widest nx-muted">Temporizadores</h3>
                    <div id="nx-timers" class="space-y-2"></div>
                    <div class="flex flex-wrap gap-2">
                        ${[1, 3, 5, 10].map(m => `<button class="nx-btn nx-btn-ghost" onclick="iniciarTemporizador(${m * 60}, '${m} min')">+ ${m} min</button>`).join("")}
                        ${receta.tiempo_preparacion_min ? `<button class="nx-btn nx-btn-ghost" onclick="iniciarTemporizador(${receta.tiempo_preparacion_min * 60}, 'Receta completa')">Receta ${receta.tiempo_preparacion_min} min</button>` : ""}
                    </div>
                </section>
            </div>

            ${pasos.length ? `
            <div class="fixed bottom-0 inset-x-0 p-4" style="background: linear-gradient(transparent, var(--nx-surface-2) 35%)">
                <div class="max-w-2xl mx-auto flex gap-3">
                    <button class="nx-btn nx-btn-ghost flex-1 !py-3" ${actual === 0 ? "disabled" : ""} onclick="irAPaso(${actual - 1})">← Anterior</button>
                    ${actual < pasos.length - 1
                        ? `<button class="nx-btn nx-btn-primary flex-[2] !py-3" onclick="irAPaso(${actual + 1})">Siguiente paso →</button>`
                        : `<button class="nx-btn nx-btn-primary flex-[2] !py-3" onclick="cerrarModoCocina()">¡Listo! 🍽</button>`}
                </div>
            </div>` : ""}`;
        actualizarTemporizadores();
    }

    function marcarIngrediente(i) {
        cocina.checks.has(i) ? cocina.checks.delete(i) : cocina.checks.add(i);
        renderizarCocina();
    }

    function irAPaso(i) {
        if (!cocina || i < 0 || i >= cocina.pasos.length) return;
        cocina.actual = i;
        renderizarCocina();
        document.querySelector(".nx-step.nx-actual")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function iniciarTemporizador(segundos, etiqueta) {
        if (!cocina) return;
        cocina.temporizadores.push({ id: Date.now() + Math.random(), etiqueta, fin: Date.now() + segundos * 1000, avisado: false });
        actualizarTemporizadores();
    }

    function quitarTemporizador(id) {
        cocina.temporizadores = cocina.temporizadores.filter(t => t.id !== id);
        actualizarTemporizadores();
    }

    function actualizarTemporizadores() {
        const cont = document.getElementById("nx-timers");
        if (!cont || !cocina) return;
        const ahora = Date.now();
        cont.innerHTML = cocina.temporizadores.map(t => {
            const restante = Math.max(0, Math.ceil((t.fin - ahora) / 1000));
            if (restante === 0 && !t.avisado) { t.avisado = true; avisarFin(t.etiqueta); }
            const mm = String(Math.floor(restante / 60)).padStart(2, "0");
            const ss = String(restante % 60).padStart(2, "0");
            return `
                <div class="nx-timer${restante === 0 ? " nx-fin" : ""}">
                    <span class="text-sm">${esc(t.etiqueta)}</span>
                    <span class="font-mono text-xl font-bold">${restante === 0 ? "¡Tiempo!" : `${mm}:${ss}`}</span>
                    <button class="nx-muted px-1" onclick="quitarTemporizador(${t.id})" aria-label="Quitar">✕</button>
                </div>`;
        }).join("") || '<p class="text-xs nx-muted">Sin temporizadores activos.</p>';
    }

    function avisarFin(etiqueta) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            [0, 0.35, 0.7].forEach(t => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.frequency.value = 880;
                gain.gain.setValueAtTime(0.25, ctx.currentTime + t);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.3);
                osc.connect(gain).connect(ctx.destination);
                osc.start(ctx.currentTime + t);
                osc.stop(ctx.currentTime + t + 0.3);
            });
        } catch (e) { /* sin audio */ }
        navigator.vibrate?.([300, 150, 300]);
        if (document.hidden && "Notification" in window && Notification.permission === "granted") {
            new Notification("NutriAI · Temporizador", { body: `${etiqueta}: ¡tiempo!` });
        }
    }

    function cerrar(id) { document.getElementById(id)?.remove(); }

    // Botón flotante de registro rápido
    function crearFab() {
        if (document.getElementById("nx-fab")) return;
        const fab = document.createElement("button");
        fab.id = "nx-fab";
        fab.className = "nx-fab";
        fab.title = "Registro rápido por voz";
        fab.setAttribute("aria-label", "Registro rápido por voz");
        fab.textContent = "🎙";
        fab.onclick = abrirRegistroRapido;
        document.body.appendChild(fab);
    }

    Object.assign(window, {
        cargarRacha, abrirRegistroRapido, cerrarRegistroRapido, alternarDictado, interpretarRegistroRapido,
        editarItemRapido, quitarItemRapido, guardarRegistroRapido,
        abrirModoCocina, cerrarModoCocina, marcarIngrediente, irAPaso, iniciarTemporizador, quitarTemporizador
    });

    // Cada vez que el diario se recarga (registro, borrado, receta consumida, agente) se repinta la racha
    if (typeof window.cargarResumenDiario === "function") {
        const recargarDiario = window.cargarResumenDiario;
        window.cargarResumenDiario = async function (...args) {
            const r = await recargarDiario.apply(this, args);
            cargarRacha();
            return r;
        };
    }

    crearFab();
    cargarRacha();
})();
