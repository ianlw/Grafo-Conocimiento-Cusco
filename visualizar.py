"""
Visualizador Web Interactivo del Grafo de Conocimiento Histórico del Cusco
==========================================================================
Carga 'data/grafo.json' y levanta un servidor HTTP local con una interfaz
interactiva moderna (Vis.js Network) para explorar el grafo sin necesidad de Neo4j.

Uso:
    python visualizar.py
    python run.py --visualizar
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
      background: #0f141c;
      color: #e2e8f0;
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    #sidebar {
      width: 360px;
      background: #182232;
      border-right: 1px solid #2d3d54;
      display: flex;
      flex-direction: column;
      z-index: 10;
      box-shadow: 2px 0 10px rgba(0,0,0,0.5);
    }
    #sidebar-header {
      padding: 16px;
      border-bottom: 1px solid #2d3d54;
      background: #111a28;
    }
    #sidebar-header h1 {
      font-size: 1.05rem;
      color: #60a5fa;
      margin-bottom: 4px;
    }
    #sidebar-header p {
      font-size: 0.78rem;
      color: #94a3b8;
    }
    .panel-section {
      padding: 12px 16px;
      border-bottom: 1px solid #233147;
    }
    .panel-section h3 {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
      margin-bottom: 8px;
    }
    input[type="text"] {
      width: 100%;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #334155;
      background: #0f172a;
      color: #f8fafc;
      font-size: 0.85rem;
      outline: none;
    }
    input[type="text"]:focus {
      border-color: #38bdf8;
    }
    .legend-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      font-size: 0.75rem;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      user-select: none;
      padding: 3px 6px;
      border-radius: 4px;
      background: #0f172a;
      transition: opacity 0.2s;
    }
    .legend-item.dimmed {
      opacity: 0.35;
    }
    .legend-badge {
      width: 12px;
      height: 12px;
      border-radius: 3px;
      flex-shrink: 0;
    }
    #node-details {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      font-size: 0.82rem;
    }
    #node-details h2 {
      font-size: 1.0rem;
      color: #f1f5f9;
      margin-bottom: 8px;
      word-break: break-word;
    }
    .detail-tag {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.72rem;
      font-weight: 600;
      margin-bottom: 12px;
    }
    .prop-row {
      margin-bottom: 8px;
      border-bottom: 1px solid #233147;
      padding-bottom: 6px;
    }
    .prop-label {
      color: #94a3b8;
      font-size: 0.72rem;
      text-transform: uppercase;
    }
    .prop-val {
      color: #f8fafc;
      margin-top: 2px;
      word-break: break-word;
    }
    .quote-box {
      background: #09131f;
      border-left: 3px solid #f59e0b;
      padding: 8px 10px;
      margin-top: 6px;
      font-style: italic;
      color: #fde68a;
      line-height: 1.35;
      font-size: 0.78rem;
    }
    #network-container {
      flex: 1;
      position: relative;
      height: 100%;
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
      backdrop-filter: blur(4px);
      padding: 8px 14px;
      border-radius: 8px;
      border: 1px solid #334155;
      font-size: 0.75rem;
      color: #94a3b8;
      z-index: 5;
    }
    #stats-badge b { color: #38bdf8; }
  </style>
</head>
<body>
  <div id="sidebar">
    <div id="sidebar-header">
      <h1>Grafo Cusco: Exp. 18 (1806)</h1>
      <p>Causas Criminales — Fondo Intendencia</p>
    </div>

    <div class="panel-section">
      <h3>Buscar Entidad</h3>
      <input type="text" id="search-input" placeholder="Nombre, lugar o evento..." oninput="filtrarNodos()">
    </div>

    <div class="panel-section">
      <h3>Filtrar por Etiqueta</h3>
      <div class="legend-grid" id="legend-grid"></div>
    </div>

    <div id="node-details">
      <p style="color:#64748b; text-align: center; margin-top: 40px;">
        Haz clic en cualquier nodo para ver sus detalles ontológicos, roles y citas textuales.
      </p>
    </div>
  </div>

  <div id="network-container">
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
    let etiquetasActivas = new Set(Object.keys(COLORES));

    async function init() {
      try {
        const resp = await fetch("/grafo.json");
        const data = await resp.json();

        todosNodos = data.nodos.map(n => {
          const color = COLORES[n.etiqueta] || "#94a3b8";
          let label = n.nombre || n.tipo || n.tipo_evento || n.descripcion || n.id;
          if (label && label.length > 22) label = label.substring(0, 20) + "...";
          return {
            id: n.id,
            label: label,
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

        todasAristas = data.aristas.map((e, idx) => ({
          id: "e_" + idx,
          from: e.origen,
          to: e.destino,
          label: e.tipo,
          font: { color: "#64748b", size: 8, strokeWidth: 0 },
          arrows: "to",
          color: { color: "#334155", highlight: "#38bdf8" },
          smooth: { type: "continuous" }
        }));

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

      } catch (err) {
        document.getElementById("badge-info").innerText = "Error cargando data/grafo.json: " + err;
      }
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

    function filtrarNodos() {
      const query = document.getElementById("search-input").value.toLowerCase().trim();
      const nodosFiltrados = todosNodos.filter(n => {
        const matchEtiq = etiquetasActivas.has(n.raw.etiqueta);
        if (!matchEtiq) return false;
        if (!query) return true;
        const texto = JSON.stringify(n.raw).toLowerCase();
        return texto.includes(query);
      });

      const idsVisibles = new Set(nodosFiltrados.map(n => n.id));
      const aristasFiltradas = todasAristas.filter(e => idsVisibles.has(e.from) && idsVisibles.has(e.to));

      nodosDataSet.clear();
      nodosDataSet.add(nodosFiltrados);
      aristasDataSet.clear();
      aristasDataSet.add(aristasFiltradas);
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
