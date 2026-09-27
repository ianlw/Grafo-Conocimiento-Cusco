"""
Visualizador Web Interactivo del Grafo de Conocimiento Histórico del Cusco
==========================================================================
Carga 'data/grafo.json' y levanta un servidor HTTP local con una interfaz
interactiva moderna (Vis.js Network) para explorar el grafo sin necesidad de Neo4j.

Opciones de visualización integradas:
  - Mostrar / Ocultar nombres de nodos
  - Mostrar / Ocultar nombres de conexiones (relaciones)
  - Filtro interactivo de tipos de aristas (ocultar MENCIONADO_EN para ver solo la red de litigio)
  - Pausar / Reanudar simulación física (Barnes-Hut)
  - Centrar / Ajustar vista (zoom inteligente)
  - Búsqueda en tiempo real por nombre, cargo, evento o cita
  - Filtros ontológicos y panel de evidencias textuales
"""

import http.server
import json
import os
import socketserver
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
GRAFO_JSON = DATA_DIR / "grafo.json"
PUERTO = 8080

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Grafo de Conocimiento Histórico — Archivo Regional del Cusco</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0b0f17;
      color: #e2e8f0;
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    #sidebar {
      width: 380px;
      background: #141c2b;
      border-right: 1px solid #233147;
      display: flex;
      flex-direction: column;
      z-index: 10;
      box-shadow: 4px 0 16px rgba(0,0,0,0.5);
    }
    #sidebar-header {
      padding: 16px;
      border-bottom: 1px solid #233147;
      background: #0f1726;
    }
    #sidebar-header h1 {
      font-size: 1.05rem;
      color: #38bdf8;
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #sidebar-header p {
      font-size: 0.76rem;
      color: #94a3b8;
    }
    .scroll-panel {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }
    .panel-section {
      padding: 12px 16px;
      border-bottom: 1px solid #1e293b;
    }
    .panel-section h3 {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #94a3b8;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    input[type="text"] {
      width: 100%;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #334155;
      background: #090d16;
      color: #f8fafc;
      font-size: 0.82rem;
      outline: none;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus {
      border-color: #38bdf8;
    }

    /* Switch Toggles */
    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px 0;
      font-size: 0.8rem;
      color: #cbd5e1;
    }
    .toggle-switch {
      position: relative;
      display: inline-block;
      width: 38px;
      height: 20px;
    }
    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .slider {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #334155;
      transition: .25s;
      border-radius: 20px;
    }
    .slider:before {
      position: absolute;
      content: "";
      height: 14px;
      width: 14px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: .25s;
      border-radius: 50%;
    }
    input:checked + .slider {
      background-color: #0284c7;
    }
    input:checked + .slider:before {
      transform: translateX(18px);
    }

    /* Action Buttons */
    .btn-group {
      display: flex;
      gap: 6px;
      margin-top: 6px;
    }
    .btn-action {
      flex: 1;
      padding: 6px 10px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 6px;
      color: #e2e8f0;
      font-size: 0.74rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      transition: all 0.15s;
    }
    .btn-action:hover {
      background: #334155;
      color: #38bdf8;
    }

    /* Grids */
    .legend-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 5px;
      font-size: 0.74rem;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      user-select: none;
      padding: 4px 6px;
      border-radius: 4px;
      background: #0c121d;
      border: 1px solid transparent;
      transition: all 0.15s;
    }
    .legend-item:hover {
      border-color: #334155;
    }
    .legend-item.dimmed {
      opacity: 0.35;
      background: #070a10;
    }
    .legend-badge {
      width: 10px;
      height: 10px;
      border-radius: 3px;
      flex-shrink: 0;
    }

    .edge-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 4px;
    }
    .edge-chip {
      padding: 3px 7px;
      border-radius: 4px;
      background: #0c121d;
      border: 1px solid #1e293b;
      font-size: 0.68rem;
      color: #94a3b8;
      cursor: pointer;
      transition: all 0.15s;
      user-select: none;
    }
    .edge-chip:hover {
      border-color: #38bdf8;
      color: #e2e8f0;
    }
    .edge-chip.active {
      background: #0369a1;
      border-color: #38bdf8;
      color: #ffffff;
    }

    /* Node Details */
    #node-details {
      padding: 16px;
      font-size: 0.8rem;
    }
    #node-details h2 {
      font-size: 0.96rem;
      color: #f1f5f9;
      margin-bottom: 6px;
      word-break: break-word;
    }
    .detail-tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.7rem;
      font-weight: 600;
      margin-bottom: 12px;
    }
    .prop-row {
      margin-bottom: 8px;
      border-bottom: 1px solid #1e293b;
      padding-bottom: 6px;
    }
    .prop-label {
      color: #64748b;
      font-size: 0.68rem;
      text-transform: uppercase;
      font-weight: 600;
    }
    .prop-val {
      color: #f8fafc;
      margin-top: 2px;
      word-break: break-word;
    }
    .quote-box {
      background: #080f1a;
      border-left: 3px solid #f59e0b;
      padding: 8px 10px;
      margin-top: 6px;
      font-style: italic;
      color: #fde68a;
      line-height: 1.35;
      font-size: 0.76rem;
      border-radius: 0 4px 4px 0;
    }

    #network-container {
      flex: 1;
      position: relative;
      height: 100%;
      background: radial-gradient(circle at center, #111a28 0%, #080c13 100%);
    }
    #network {
      width: 100%;
      height: 100%;
    }
    #stats-badge {
      position: absolute;
      bottom: 12px;
      right: 12px;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(6px);
      padding: 8px 14px;
      border-radius: 8px;
      border: 1px solid #334155;
      font-size: 0.74rem;
      color: #94a3b8;
      z-index: 5;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    #stats-badge b { color: #38bdf8; }

    /* Floating quick toolbar */
    #quick-toolbar {
      position: absolute;
      top: 14px;
      right: 14px;
      display: flex;
      gap: 8px;
      z-index: 5;
    }
    .quick-btn {
      background: rgba(15, 23, 42, 0.88);
      backdrop-filter: blur(6px);
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.74rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .quick-btn:hover {
      background: #1e293b;
      border-color: #38bdf8;
      color: #38bdf8;
    }
  </style>
</head>
<body>
  <div id="sidebar">
    <div id="sidebar-header">
      <h1>🏛️ Grafo Cusco: Exp. 18 (1806)</h1>
      <p>Fondo Intendencia — Causas Criminales</p>
    </div>

    <div class="scroll-panel">
      <!-- 1. Búsqueda -->
      <div class="panel-section">
        <h3>🔍 Buscar Entidad</h3>
        <input type="text" id="search-input" placeholder="Huancachoque, Chuquitapa, Tinta..." oninput="filtrarNodos()">
      </div>

      <!-- 2. Opciones de Visualización Solicitadas -->
      <div class="panel-section">
        <h3>⚙️ Opciones de Visualización</h3>
        
        <div class="toggle-row">
          <span>Mostrar nombres de nodos</span>
          <label class="toggle-switch">
            <input type="checkbox" id="toggle-node-labels" checked onchange="actualizarNombresNodos(this.checked)">
            <span class="slider"></span>
          </label>
        </div>

        <div class="toggle-row">
          <span>Mostrar nombres de conexiones</span>
          <label class="toggle-switch">
            <input type="checkbox" id="toggle-edge-labels" checked onchange="actualizarNombresAristas(this.checked)">
            <span class="slider"></span>
          </label>
        </div>

        <div class="toggle-row">
          <span>Simulación física activa</span>
          <label class="toggle-switch">
            <input type="checkbox" id="toggle-physics" checked onchange="actualizarFisica(this.checked)">
            <span class="slider"></span>
          </label>
        </div>

        <div class="btn-group">
          <button class="btn-action" onclick="centrarGrafo()">
            🎯 Centrar vista
          </button>
          <button class="btn-action" onclick="aislarRedConflicto()">
            ⚡ Red del Conflicto
          </button>
        </div>
      </div>

      <!-- 3. Filtro por Tipos de Nodos (Clases Ontológicas) -->
      <div class="panel-section">
        <h3>🏷️ Clases Ontológicas</h3>
        <div class="legend-grid" id="legend-grid"></div>
      </div>

      <!-- 4. Filtro por Tipos de Aristas (Relaciones) -->
      <div class="panel-section">
        <h3>🔗 Tipos de Conexión</h3>
        <div class="edge-chips" id="edge-chips"></div>
      </div>

      <!-- 5. Detalles del Nodo Seleccionado -->
      <div id="node-details">
        <p style="color:#64748b; text-align: center; margin-top: 30px;">
          Haz clic en cualquier nodo para ver sus detalles ontológicos, roles y citas textuales de evidencia.
        </p>
      </div>
    </div>
  </div>

  <div id="network-container">
    <div id="quick-toolbar">
      <button class="quick-btn" onclick="centrarGrafo()" title="Ajusta el zoom para ver todos los nodos">
        🔍 Centrar
      </button>
      <button class="quick-btn" id="btn-quick-physics" onclick="toggleFisicaQuick()" title="Pausar o reanudar el algoritmo de resortes">
        ⏸ Pausar Física
      </button>
      <button class="quick-btn" onclick="alternarTodosNombres()" title="Alternar visibilidad de etiquetas">
        🏷️ Alternar Nombres
      </button>
    </div>

    <div id="network"></div>

    <div id="stats-badge">
      <span id="badge-info">Cargando grafo...</span>
    </div>
  </div>

  <script>
    const COLORES = {
      "Actor": "#3b82f6",
      "FuenteArchivistica": "#64748b",
      "Lugar": "#10b981",
      "ObjetoBien": "#8b5cf6",
      "EventoInstitucional": "#06b6d4",
      "EventoTestimoniado": "#f97316",
      "AfirmacionHistorica": "#eab308"
    };

    let network = null;
    let todosNodos = [];
    let todasAristas = [];
    let nodosDataSet = null;
    let aristasDataSet = null;

    let mostrarNombresNodos = true;
    let mostrarNombresAristas = true;
    let fisicaHabilitada = true;

    let etiquetasActivas = new Set(Object.keys(COLORES));
    let tiposAristasActivos = new Set();

    async function init() {
      try {
        const resp = await fetch("/grafo.json");
        const data = await resp.json();

        // 1. Preparar nodos con sus etiquetas originales
        todosNodos = data.nodos.map(n => {
          const color = COLORES[n.etiqueta] || "#94a3b8";
          let label = n.nombre || n.tipo || n.tipo_evento || n.descripcion || n.id;
          if (label && label.length > 24) label = label.substring(0, 22) + "...";
          return {
            id: n.id,
            label: label,
            labelOriginal: label,
            title: n.nombre || n.id,
            color: { background: color, border: "#1e293b", highlight: { background: "#ffffff", border: color } },
            font: { color: "#ffffff", size: 11, face: "sans-serif" },
            shape: n.etiqueta === "AfirmacionHistorica" ? "diamond" :
                   n.etiqueta === "FuenteArchivistica" ? "box" :
                   n.etiqueta === "Actor" ? "dot" : "ellipse",
            size: n.etiqueta === "Actor" ? 18 : 14,
            raw: n
          };
        });

        // 2. Preparar aristas
        const tiposUnicos = new Set();
        todasAristas = data.aristas.map((e, idx) => {
          tiposUnicos.add(e.tipo);
          return {
            id: "e_" + idx,
            from: e.origen,
            to: e.destino,
            label: e.tipo,
            labelOriginal: e.tipo,
            tipoOriginal: e.tipo,
            font: { color: "#64748b", size: 8, strokeWidth: 0 },
            arrows: "to",
            color: { color: "#334155", highlight: "#38bdf8" },
            smooth: { type: "continuous" }
          };
        });

        tiposAristasActivos = new Set(tiposUnicos);

        nodosDataSet = new vis.DataSet(todosNodos);
        aristasDataSet = new vis.DataSet(todasAristas);

        const container = document.getElementById("network");
        const visData = { nodes: nodosDataSet, edges: aristasDataSet };
        const options = {
          physics: {
            stabilization: { iterations: 120 },
            barnesHut: { gravitationalConstant: -2800, springLength: 95, springConstant: 0.04 }
          },
          interaction: { hover: true, tooltipDelay: 200, multiselect: false }
        };

        network = new vis.Network(container, visData, options);

        network.on("click", function(params) {
          if (params.nodes.length > 0) {
            mostrarDetallesNodo(params.nodes[0]);
          }
        });

        document.getElementById("badge-info").innerHTML =
          `Nodos: <b>${data.nodos.length}</b> | Aristas: <b>${data.aristas.length}</b>`;

        construirLeyenda(data.resumen.por_etiqueta);
        construirFiltrosAristas(Array.from(tiposUnicos).sort());

      } catch (err) {
        document.getElementById("badge-info").innerText = "Error cargando data/grafo.json: " + err;
      }
    }

    // Toggle de nombres de nodos
    function actualizarNombresNodos(activo) {
      mostrarNombresNodos = activo;
      document.getElementById("toggle-node-labels").checked = activo;
      filtrarNodos();
    }

    // Toggle de nombres de conexiones / aristas
    function actualizarNombresAristas(activo) {
      mostrarNombresAristas = activo;
      document.getElementById("toggle-edge-labels").checked = activo;
      filtrarNodos();
    }

    // Alternar ambos nombres con botón rápido
    function alternarTodosNombres() {
      const nuevo = !mostrarNombresNodos;
      actualizarNombresNodos(nuevo);
      actualizarNombresAristas(nuevo);
    }

    // Control de física
    function actualizarFisica(activo) {
      fisicaHabilitada = activo;
      document.getElementById("toggle-physics").checked = activo;
      network.setOptions({ physics: { enabled: activo } });
      const quickBtn = document.getElementById("btn-quick-physics");
      quickBtn.innerHTML = activo ? "⏸ Pausar Física" : "▶ Reanudar Física";
    }

    function toggleFisicaQuick() {
      actualizarFisica(!fisicaHabilitada);
    }

    // Centrar vista con animación
    function centrarGrafo() {
      if (network) {
        network.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
      }
    }

    // Aislar la red del conflicto principal (oculta fuentes archivísticas para claridad)
    function aislarRedConflicto() {
      if (etiquetasActivas.has("FuenteArchivistica")) {
        etiquetasActivas.delete("FuenteArchivistica");
        document.getElementById("legend-FuenteArchivistica")?.classList.add("dimmed");
      } else {
        etiquetasActivas.add("FuenteArchivistica");
        document.getElementById("legend-FuenteArchivistica")?.classList.remove("dimmed");
      }
      filtrarNodos();
      setTimeout(centrarGrafo, 300);
    }

    function construirLeyenda(conteo) {
      const grid = document.getElementById("legend-grid");
      grid.innerHTML = "";
      for (const [etiq, col] of Object.entries(COLORES)) {
        const count = conteo[etiq] || 0;
        const item = document.createElement("div");
        item.className = "legend-item";
        item.id = "legend-" + etiq;
        item.innerHTML = `<span class="legend-badge" style="background:${col}"></span><span>${etiq} (${count})</span>`;
        item.onclick = () => alternarEtiqueta(etiq);
        grid.appendChild(item);
      }
    }

    function construirFiltrosAristas(tipos) {
      const container = document.getElementById("edge-chips");
      container.innerHTML = "";
      for (const t of tipos) {
        const chip = document.createElement("span");
        chip.className = "edge-chip active";
        chip.id = "chip-" + t;
        chip.innerText = t;
        chip.onclick = () => alternarTipoArista(t);
        container.appendChild(chip);
      }
    }

    function alternarEtiqueta(etiq) {
      if (etiquetasActivas.has(etiq)) {
        etiquetasActivas.delete(etiq);
        document.getElementById("legend-" + etiq).classList.add("dimmed");
      } else {
        etiquetasActivas.add(etiq);
        document.getElementById("legend-" + etiq).classList.remove("dimmed");
      }
      filtrarNodos();
    }

    function alternarTipoArista(tipo) {
      const chip = document.getElementById("chip-" + tipo);
      if (tiposAristasActivos.has(tipo)) {
        tiposAristasActivos.delete(tipo);
        chip.classList.remove("active");
      } else {
        tiposAristasActivos.add(tipo);
        chip.classList.add("active");
      }
      filtrarNodos();
    }

    function filtrarNodos() {
      const query = document.getElementById("search-input").value.toLowerCase().trim();

      // Nodos filtrados según etiqueta y búsqueda
      const nodosFiltrados = todosNodos.filter(n => {
        const matchEtiq = etiquetasActivas.has(n.raw.etiqueta);
        if (!matchEtiq) return false;
        if (!query) return true;
        const texto = JSON.stringify(n.raw).toLowerCase();
        return texto.includes(query);
      }).map(n => ({
        ...n,
        label: mostrarNombresNodos ? n.labelOriginal : ""
      }));

      const idsVisibles = new Set(nodosFiltrados.map(n => n.id));

      // Aristas filtradas según nodos visibles y tipos de aristas activos
      const aristasFiltradas = todasAristas.filter(e => {
        return idsVisibles.has(e.from) && idsVisibles.has(e.to) && tiposAristasActivos.has(e.tipoOriginal);
      }).map(e => ({
        ...e,
        label: mostrarNombresAristas ? e.labelOriginal : ""
      }));

      nodosDataSet.clear();
      nodosDataSet.add(nodosFiltrados);
      aristasDataSet.clear();
      aristasDataSet.add(aristasFiltradas);

      document.getElementById("badge-info").innerHTML =
        `Visibles: Nodos <b>${nodosFiltrados.length}</b> / Aristas <b>${aristasFiltradas.length}</b>`;
    }

    function mostrarDetallesNodo(nodeId) {
      const nodo = todosNodos.find(n => n.id === nodeId);
      if (!nodo) return;
      const raw = nodo.raw;
      const col = COLORES[raw.etiqueta] || "#94a3b8";

      let html = `<h2>${raw.nombre || raw.tipo_evento || raw.descripcion || raw.id}</h2>`;
      html += `<div class="detail-tag" style="background:${col}33; color:${col}; border:1px solid ${col}">${raw.etiqueta}</div>`;

      for (const [k, v] of Object.entries(raw)) {
        if (["id", "etiqueta"].includes(k) || v === null || v === undefined) continue;
        if (k === "cita") {
          html += `<div class="prop-row"><div class="prop-label">Cita Evidencia</div><div class="quote-box">"${v}"</div></div>`;
        } else if (Array.isArray(v)) {
          if (v.length > 0) {
            html += `<div class="prop-row"><div class="prop-label">${k}</div><div class="prop-val">${v.join(", ")}</div></div>`;
          }
        } else {
          html += `<div class="prop-row"><div class="prop-label">${k}</div><div class="prop-val">${v}</div></div>`;
        }
      }

      document.getElementById("node-details").innerHTML = html;
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class GrafoHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return
        elif self.path == "/grafo.json":
            if not GRAFO_JSON.exists():
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error": "grafo.json no encontrado"}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            with open(GRAFO_JSON, "rb") as f:
                self.wfile.write(f.read())
            return
        super().do_GET()

    def log_message(self, format, *args):
        # Silenciar logs ruidosos de peticiones
        pass


def iniciar_visualizador(puerto: int = PUERTO):
    """Inicia el servidor web local y abre el visualizador en el navegador."""
    if not GRAFO_JSON.exists():
        print(f"\n[visualizador] ERROR: No se encuentra {GRAFO_JSON}")
        print("Ejecuta primero: python run.py --solo-grafo")
        return

    url = f"http://localhost:{puerto}"
    print("\n" + "=" * 60)
    print("  VISUALIZADOR WEB INTERACTIVO DEL GRAFO DE CUSCO")
    print("=" * 60)
    print(f"  Abriendo en tu navegador: {url}")
    print("  Presiona Ctrl+C en la terminal para detener el servidor.\n")

    webbrowser.open(url)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", puerto), GrafoHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[visualizador] Servidor web detenido.")


if __name__ == "__main__":
    iniciar_visualizador()
