"""
Visualizador Web Interactivo del Grafo de Conocimiento Histórico del Cusco
==========================================================================
Carga 'data/grafo.json' y levanta un servidor HTTP local con una interfaz
interactiva moderna con soporte dual para visualización 2D (Vis.js) y 3D (WebGL / Three.js).

Características principales:
  - Modo Dual: Conmutador fluido entre Grafo 2D y Grafo 3D (WebGL)
  - Control de visualización: Mostrar / Ocultar nombres de nodos
  - Control de conexiones: Mostrar / Ocultar etiquetas de aristas
  - Panel lateral colapsable / expandible con botón flotante
  - Modo Pantalla Completa nativo (Fullscreen API)
  - Auto-rotación y controles de órbita 3D
  - Filtros ontológicos y de relaciones (ocultar MENCIONADO_EN para red limpia)
  - Búsqueda en tiempo real e inspector lateral de citas y procedencia
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
  <!-- Vis.js para modo 2D -->
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <!-- 3D Force Graph y Three SpriteText para modo 3D WebGL -->
  <script src="https://unpkg.com/3d-force-graph"></script>
  <script src="https://unpkg.com/three-spritetext"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #070a10;
      color: #e2e8f0;
      display: flex;
      height: 100vh;
      overflow: hidden;
    }

    /* Panel Lateral */
    #sidebar {
      width: 380px;
      min-width: 380px;
      background: #111723;
      border-right: 1px solid #1e293b;
      display: flex;
      flex-direction: column;
      z-index: 10;
      box-shadow: 4px 0 20px rgba(0,0,0,0.6);
      transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    #sidebar.collapsed {
      margin-left: -380px;
    }
    #sidebar-header {
      padding: 16px;
      border-bottom: 1px solid #1e293b;
      background: #0c121d;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #sidebar-header .title-box h1 {
      font-size: 1.02rem;
      color: #38bdf8;
      margin-bottom: 3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #sidebar-header .title-box p {
      font-size: 0.74rem;
      color: #94a3b8;
    }
    .btn-close-sidebar {
      background: #1e293b;
      border: 1px solid #334155;
      color: #94a3b8;
      border-radius: 6px;
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 0.85rem;
      transition: all 0.15s;
    }
    .btn-close-sidebar:hover {
      color: #f8fafc;
      border-color: #38bdf8;
    }

    .scroll-panel {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }
    .panel-section {
      padding: 12px 16px;
      border-bottom: 1px solid #1a2333;
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

    /* Conmutador Modo 2D / 3D */
    .mode-switch {
      display: flex;
      background: #070a10;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 3px;
      margin-bottom: 8px;
    }
    .mode-btn {
      flex: 1;
      padding: 6px 10px;
      background: transparent;
      border: none;
      border-radius: 4px;
      color: #94a3b8;
      font-size: 0.76rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .mode-btn.active {
      background: #0284c7;
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }

    input[type="text"] {
      width: 100%;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #334155;
      background: #070a10;
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
      font-size: 0.78rem;
      color: #cbd5e1;
    }
    .toggle-switch {
      position: relative;
      display: inline-block;
      width: 36px;
      height: 19px;
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
      transition: .2s;
      border-radius: 20px;
    }
    .slider:before {
      position: absolute;
      content: "";
      height: 13px;
      width: 13px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: .2s;
      border-radius: 50%;
    }
    input:checked + .slider {
      background-color: #0284c7;
    }
    input:checked + .slider:before {
      transform: translateX(17px);
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
      font-size: 0.73rem;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      user-select: none;
      padding: 4px 6px;
      border-radius: 4px;
      background: #090e17;
      border: 1px solid transparent;
      transition: all 0.15s;
    }
    .legend-item:hover {
      border-color: #334155;
    }
    .legend-item.dimmed {
      opacity: 0.35;
      background: #05070c;
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
      background: #090e17;
      border: 1px solid #1e293b;
      font-size: 0.67rem;
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

    /* Contenedor del Grafo */
    #network-container {
      flex: 1;
      position: relative;
      height: 100%;
      background: radial-gradient(circle at center, #0e1522 0%, #05080e 100%);
      overflow: hidden;
    }
    #network-2d, #network-3d {
      width: 100%;
      height: 100%;
      position: absolute;
      top: 0;
      left: 0;
    }
    #network-3d {
      display: none;
    }

    /* Botón flotante para abrir/cerrar sidebar */
    #btn-toggle-sidebar {
      position: absolute;
      top: 14px;
      left: 14px;
      z-index: 20;
      background: rgba(17, 23, 35, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.76rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    #btn-toggle-sidebar:hover {
      background: #1e293b;
      border-color: #38bdf8;
      color: #38bdf8;
    }

    /* Barra de herramientas flotante superior derecha */
    #quick-toolbar {
      position: absolute;
      top: 14px;
      right: 14px;
      display: flex;
      gap: 8px;
      z-index: 20;
    }
    .quick-btn {
      background: rgba(17, 23, 35, 0.9);
      backdrop-filter: blur(8px);
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
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .quick-btn:hover {
      background: #1e293b;
      border-color: #38bdf8;
      color: #38bdf8;
    }

    #stats-badge {
      position: absolute;
      bottom: 12px;
      right: 12px;
      background: rgba(15, 23, 42, 0.88);
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
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    #stats-badge b { color: #38bdf8; }
  </style>
</head>
<body>
  <!-- Panel Lateral -->
  <div id="sidebar">
    <div id="sidebar-header">
      <div class="title-box">
        <h1>🏛️ Grafo Cusco: Exp. 18</h1>
        <p>Fondo Intendencia — Causas Criminales (1806)</p>
      </div>
      <button class="btn-close-sidebar" onclick="alternarSidebar()" title="Ocultar panel lateral">◀</button>
    </div>

    <div class="scroll-panel">
      <!-- Conmutador 2D / 3D -->
      <div class="panel-section">
        <h3>🌌 Modo de Renderizado</h3>
        <div class="mode-switch">
          <button class="mode-btn active" id="btn-mode-2d" onclick="cambiarModo('2D')">
            📊 Grafo 2D
          </button>
          <button class="mode-btn" id="btn-mode-3d" onclick="cambiarModo('3D')">
            🪐 Grafo 3D (WebGL)
          </button>
        </div>
      </div>

      <!-- Búsqueda -->
      <div class="panel-section">
        <h3>🔍 Buscar Entidad</h3>
        <input type="text" id="search-input" placeholder="Huancachoque, Chuquitapa, Tinta..." oninput="filtrarNodos()">
      </div>

      <!-- Opciones de Visualización Solicitadas -->
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

        <div class="toggle-row" id="row-autorotate-3d" style="display:none;">
          <span>Auto-rotación 3D</span>
          <label class="toggle-switch">
            <input type="checkbox" id="toggle-autorotate" onchange="actualizarAutoRotacion(this.checked)">
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

      <!-- Filtro por Clases Ontológicas -->
      <div class="panel-section">
        <h3>🏷️ Clases Ontológicas</h3>
        <div class="legend-grid" id="legend-grid"></div>
      </div>

      <!-- Filtro por Tipos de Conexión -->
      <div class="panel-section">
        <h3>🔗 Tipos de Conexión</h3>
        <div class="edge-chips" id="edge-chips"></div>
      </div>

      <!-- Detalles del Nodo Seleccionado -->
      <div id="node-details">
        <p style="color:#64748b; text-align: center; margin-top: 30px;">
          Haz clic en cualquier nodo para ver sus detalles ontológicos, roles y citas textuales de evidencia.
        </p>
      </div>
    </div>
  </div>

  <!-- Contenedor del Grafo -->
  <div id="network-container">
    <!-- Botón flotante para colapsar / expandir panel izquierdo -->
    <button id="btn-toggle-sidebar" onclick="alternarSidebar()" title="Ocultar o mostrar panel lateral">
      <span id="sidebar-icon">◀</span> <span id="sidebar-text">Ocultar Panel</span>
    </button>

    <!-- Barra de herramientas flotante superior derecha -->
    <div id="quick-toolbar">
      <button class="quick-btn" id="btn-quick-mode" onclick="toggleModoRapido()" title="Alternar entre visualización 2D y 3D">
        🪐 Modo 3D
      </button>
      <button class="quick-btn" onclick="centrarGrafo()" title="Ajusta el zoom para ver todo el grafo">
        🔍 Centrar
      </button>
      <button class="quick-btn" id="btn-quick-physics" onclick="toggleFisicaQuick()" title="Pausar o reanudar el cálculo de resortes">
        ⏸ Pausar Física
      </button>
      <button class="quick-btn" id="btn-fullscreen" onclick="alternarPantallaCompleta()" title="Ver en pantalla completa">
        ⛶ Pantalla Completa
      </button>
    </div>

    <!-- Lienzo 2D (Vis.js) -->
    <div id="network-2d"></div>

    <!-- Lienzo 3D (3D Force Graph WebGL) -->
    <div id="network-3d"></div>

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

    let modoActual = "2D";
    let network2D = null;
    let graph3D = null;

    let todosNodos = [];
    let todasAristas = [];
    let nodosDataSet = null;
    let aristasDataSet = null;

    let mostrarNombresNodos = true;
    let mostrarNombresAristas = true;
    let fisicaHabilitada = true;
    let sidebarAbierto = true;

    let etiquetasActivas = new Set(Object.keys(COLORES));
    let tiposAristasActivos = new Set();

    async function init() {
      try {
        const resp = await fetch("/grafo.json");
        const data = await resp.json();

        // 1. Preparar nodos
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
            raw: n,
            // 3D properties
            val: n.etiqueta === "Actor" ? 7 : n.etiqueta === "AfirmacionHistorica" ? 5 : 4,
            nodeColor: color
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
            source: e.origen,
            target: e.destino,
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

        // 3. Inicializar red 2D
        nodosDataSet = new vis.DataSet(todosNodos);
        aristasDataSet = new vis.DataSet(todasAristas);

        const container2D = document.getElementById("network-2d");
        const visData = { nodes: nodosDataSet, edges: aristasDataSet };
        const options2D = {
          physics: {
            stabilization: { iterations: 120 },
            barnesHut: { gravitationalConstant: -2800, springLength: 95, springConstant: 0.04 }
          },
          interaction: { hover: true, tooltipDelay: 200, multiselect: false }
        };

        network2D = new vis.Network(container2D, visData, options2D);

        network2D.on("click", function(params) {
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

    // ==========================================
    // CONTROL 2D / 3D
    // ==========================================
    function cambiarModo(nuevoModo) {
      if (nuevoModo === modoActual) return;
      modoActual = nuevoModo;

      const btn2D = document.getElementById("btn-mode-2d");
      const btn3D = document.getElementById("btn-mode-3d");
      const div2D = document.getElementById("network-2d");
      const div3D = document.getElementById("network-3d");
      const rowRotate = document.getElementById("row-autorotate-3d");
      const btnQuickMode = document.getElementById("btn-quick-mode");

      if (modoActual === "3D") {
        btn3D.classList.add("active");
        btn2D.classList.remove("active");
        div2D.style.display = "none";
        div3D.style.display = "block";
        rowRotate.style.display = "flex";
        btnQuickMode.innerHTML = "📊 Modo 2D";

        inicializarOActualizar3D();
      } else {
        btn2D.classList.add("active");
        btn3D.classList.remove("active");
        div3D.style.display = "none";
        div2D.style.display = "block";
        rowRotate.style.display = "none";
        btnQuickMode.innerHTML = "🪐 Modo 3D";

        if (network2D) {
          setTimeout(() => network2D.fit(), 100);
        }
      }
    }

    function toggleModoRapido() {
      cambiarModo(modoActual === "2D" ? "3D" : "2D");
    }

    function inicializarOActualizar3D() {
      const container3D = document.getElementById("network-3d");
      const { nodosVisibles, aristasVisibles } = obtenerElementosFiltrados();

      // Formato para 3d-force-graph
      const gData = {
        nodes: nodosVisibles.map(n => ({
          id: n.id,
          name: n.labelOriginal,
          val: n.val,
          color: n.nodeColor,
          raw: n.raw
        })),
        links: aristasVisibles.map(e => ({
          source: e.from,
          target: e.to,
          name: e.labelOriginal
        }))
      };

      if (!graph3D) {
        graph3D = ForceGraph3D()(container3D)
          .backgroundColor("#070a10")
          .graphData(gData)
          .nodeId("id")
          .nodeVal("val")
          .nodeColor("color")
          .nodeLabel(n => `<div style="background:#0f172a; padding:6px 10px; border-radius:6px; border:1px solid #38bdf8; color:#fff; font-family:sans-serif; font-size:12px;"><b>${n.name}</b> <span style="color:#94a3b8">(${n.raw.etiqueta})</span></div>`)
          .nodeResolution(16)
          .linkWidth(1.2)
          .linkColor(() => "#334155")
          .linkDirectionalArrowLength(3.5)
          .linkDirectionalArrowRelPos(1)
          .linkCurvature(0.15)
          .linkDirectionalParticles(2)
          .linkDirectionalParticleWidth(1.2)
          .linkDirectionalParticleSpeed(0.005)
          .linkLabel(l => mostrarNombresAristas ? l.name : null)
          .onNodeClick(n => {
            mostrarDetallesNodo(n.id);
            // Enfocar cámara al nodo en 3D
            const dist = 60;
            const distRatio = 1 + dist / Math.hypot(n.x, n.y, n.z);
            graph3D.cameraPosition(
              { x: n.x * distRatio, y: n.y * distRatio, z: n.z * distRatio },
              n,
              1200
            );
          });

        // Configuración de renderizado de texto 3D con SpriteText
        if (typeof SpriteText !== "undefined") {
          graph3D.nodeThreeObject(node => {
            if (!mostrarNombresNodos) return null;
            const sprite = new SpriteText(node.name);
            sprite.color = "#ffffff";
            sprite.textHeight = 4.5;
            sprite.backgroundColor = "rgba(15, 23, 42, 0.65)";
            sprite.padding = 2;
            sprite.borderRadius = 3;
            return sprite;
          });
        }

      } else {
        graph3D.graphData(gData);
        if (typeof SpriteText !== "undefined") {
          graph3D.nodeThreeObject(node => {
            if (!mostrarNombresNodos) return null;
            const sprite = new SpriteText(node.name);
            sprite.color = "#ffffff";
            sprite.textHeight = 4.5;
            sprite.backgroundColor = "rgba(15, 23, 42, 0.65)";
            sprite.padding = 2;
            sprite.borderRadius = 3;
            return sprite;
          });
        }
      }
    }

    function actualizarAutoRotacion(activo) {
      if (graph3D && graph3D.controls) {
        graph3D.controls().autoRotate = activo;
        graph3D.controls().autoRotateSpeed = 0.8;
      }
    }

    // ==========================================
    // CONTROL PANEL LATERAL (Colapsar / Expandir)
    // ==========================================
    function alternarSidebar() {
      sidebarAbierto = !sidebarAbierto;
      const sidebar = document.getElementById("sidebar");
      const icon = document.getElementById("sidebar-icon");
      const text = document.getElementById("sidebar-text");

      if (sidebarAbierto) {
        sidebar.classList.remove("collapsed");
        icon.innerText = "◀";
        text.innerText = "Ocultar Panel";
      } else {
        sidebar.classList.add("collapsed");
        icon.innerText = "▶";
        text.innerText = "Mostrar Panel";
      }

      // Reajustar dimensiones de los lienzos
      setTimeout(() => {
        if (modoActual === "2D" && network2D) {
          network2D.fit();
        } else if (modoActual === "3D" && graph3D) {
          const w = document.getElementById("network-container").clientWidth;
          const h = document.getElementById("network-container").clientHeight;
          graph3D.width(w).height(h);
        }
      }, 320);
    }

    // ==========================================
    // PANTALLA COMPLETA (Fullscreen API)
    // ==========================================
    function alternarPantallaCompleta() {
      const elem = document.documentElement;
      if (!document.fullscreenElement) {
        if (elem.requestFullscreen) {
          elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
          elem.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        }
      }
    }

    document.addEventListener("fullscreenchange", () => {
      const isFull = !!document.fullscreenElement;
      const btn = document.getElementById("btn-fullscreen");
      if (btn) {
        btn.innerHTML = isFull ? "🗗 Salir Fullscreen" : "⛶ Pantalla Completa";
      }
    });

    // ==========================================
    // CONTROLES DE ETIQUETAS Y FÍSICA
    // ==========================================
    function actualizarNombresNodos(activo) {
      mostrarNombresNodos = activo;
      document.getElementById("toggle-node-labels").checked = activo;
      filtrarNodos();
    }

    function actualizarNombresAristas(activo) {
      mostrarNombresAristas = activo;
      document.getElementById("toggle-edge-labels").checked = activo;
      filtrarNodos();
    }

    function actualizarFisica(activo) {
      fisicaHabilitada = activo;
      document.getElementById("toggle-physics").checked = activo;

      if (network2D) {
        network2D.setOptions({ physics: { enabled: activo } });
      }
      if (graph3D) {
        if (activo) {
          graph3D.resumeAnimation();
        } else {
          graph3D.pauseAnimation();
        }
      }

      const quickBtn = document.getElementById("btn-quick-physics");
      quickBtn.innerHTML = activo ? "⏸ Pausar Física" : "▶ Reanudar Física";
    }

    function toggleFisicaQuick() {
      actualizarFisica(!fisicaHabilitada);
    }

    function centrarGrafo() {
      if (modoActual === "2D" && network2D) {
        network2D.fit({ animation: { duration: 600, easingFunction: "easeInOutQuad" } });
      } else if (modoActual === "3D" && graph3D) {
        graph3D.zoomToFit(1000, 40);
      }
    }

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

    function obtenerElementosFiltrados() {
      const query = document.getElementById("search-input").value.toLowerCase().trim();

      const nodosFiltrados = todosNodos.filter(n => {
        const matchEtiq = etiquetasActivas.has(n.raw.etiqueta);
        if (!matchEtiq) return false;
        if (!query) return true;
        const texto = JSON.stringify(n.raw).toLowerCase();
        return texto.includes(query);
      });

      const idsVisibles = new Set(nodosFiltrados.map(n => n.id));

      const aristasFiltradas = todasAristas.filter(e => {
        return idsVisibles.has(e.from) && idsVisibles.has(e.to) && tiposAristasActivos.has(e.tipoOriginal);
      });

      return { nodosVisibles: nodosFiltrados, aristasVisibles: aristasFiltradas };
    }

    function filtrarNodos() {
      const { nodosVisibles, aristasVisibles } = obtenerElementosFiltrados();

      // Actualizar 2D
      if (nodosDataSet && aristasDataSet) {
        const nodos2D = nodosVisibles.map(n => ({
          ...n,
          label: mostrarNombresNodos ? n.labelOriginal : ""
        }));

        const aristas2D = aristasVisibles.map(e => ({
          ...e,
          label: mostrarNombresAristas ? e.labelOriginal : ""
        }));

        nodosDataSet.clear();
        nodosDataSet.add(nodos2D);
        aristasDataSet.clear();
        aristasDataSet.add(aristas2D);
      }

      // Actualizar 3D si está activo
      if (modoActual === "3D" && graph3D) {
        inicializarOActualizar3D();
      }

      document.getElementById("badge-info").innerHTML =
        `Visibles: Nodos <b>${nodosVisibles.length}</b> / Aristas <b>${aristasVisibles.length}</b>`;
    }

    function mostrarDetallesNodo(nodeId) {
      const nodo = todosNodos.find(n => n.id === nodeId);
      if (!nodo) return;
      const raw = nodo.raw;
      const col = COLORES[raw.etiqueta] || "#94a3b8";

      let html = `<h2>${raw.nombre || raw.tipo_evento || raw.descripcion || raw.id}</h2>`;
      html += `<div class="detail-tag" style="background:${col}33; color:${col}; border:1px solid ${col}">${raw.etiqueta}</div>`;

      for (const [k, v] of Object.entries(raw)) {
        if (["id", "etiqueta", "val", "nodeColor"].includes(k) || v === null || v === undefined) continue;
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

      // Si el panel estaba colapsado, abrirlo automáticamente para ver la evidencia
      if (!sidebarAbierto) {
        alternarSidebar();
      }
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
    print("  VISUALIZADOR WEB INTERACTIVO DEL GRAFO DE CUSCO (2D / 3D)")
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
