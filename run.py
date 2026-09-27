"""
Script de Orquestación del Pipeline Completo
=============================================
Ejecuta los tres pasos del pipeline en secuencia:

  1. SEGMENTAR: divide la transcripción en bloques por folio/acto.
  2. EXTRAER:   envía cada bloque al LLM y obtiene entidades validadas.
  3. GRAFO:     construye el grafo de conocimiento y lo exporta a JSON / Neo4j.

Uso:
    # Solo segmentar (sin llamar al LLM):
    python run.py --solo-segmentar

    # Construir grafo desde extracciones existentes:
    python run.py --solo-grafo

    # Ver grafo en navegador interactivo local:
    python run.py --visualizar

    # Evaluar calidad y estadísticas del grafo (KGCQ):
    python run.py --stats

    # Pipeline completo:
    python run.py

# Con Neo4j:
#     Linux/macOS: export NEO4J_PASSWORD='tu_password'; python run.py
#     Windows:     $env:NEO4J_PASSWORD='tu_password'; python run.py
#     (O definirlo en el archivo .env)

# Requiere:
#     - GOOGLE_API_KEY en .env o como variable de entorno
"""

import argparse
import os
import sys
from pathlib import Path


def _cargar_env(ruta_env: Path) -> None:
    """Lee el archivo .env y exporta las variables al entorno del proceso."""
    if not ruta_env.exists():
        return
    with ruta_env.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "=" in linea:
                clave, _, valor = linea.partition("=")
                clave = clave.strip()
                valor = valor.strip()
                if clave and not os.environ.get(clave):  # No sobreescribe si ya existe
                    os.environ[clave] = valor


# Carga automática del .env al importar el módulo
_cargar_env(Path(__file__).resolve().parent / ".env")

# Directorio base de GRAFO_CONOCIMIENTOS_CUSCO
PROYECTO_DIR = Path(__file__).resolve().parent
CORPUS_DIR = PROYECTO_DIR / "corpus"
DATA_DIR = PROYECTO_DIR / "data"

RUTA_TRANSCRIPCION = CORPUS_DIR / "Transcripcion_CC_L14E18.txt"
RUTA_SEGMENTOS = DATA_DIR / "segmentos.jsonl"
RUTA_EXTRACCIONES = DATA_DIR / "extracciones.jsonl"
RUTA_GRAFO = DATA_DIR / "grafo.json"

# Añadir GRAFO_CONOCIMIENTOS_CUSCO al path para imports
sys.path.insert(0, str(PROYECTO_DIR))


def paso_segmentar(ruta_archivo: Path = RUTA_TRANSCRIPCION):
    """Paso 1: Segmentación del texto por folios y actos procesales."""
    from pipeline.segmenter import segmentar_expediente, guardar_segmentos_json

    print("\n" + "="*60)
    print(f"  PASO 1: SEGMENTACIÓN DE FOLIOS -> {ruta_archivo.name}")
    print("="*60)

    segmentos = segmentar_expediente(ruta_archivo)
    guardar_segmentos_json(segmentos, RUTA_SEGMENTOS)

    print(f"\n  Total segmentos: {len(segmentos)}")
    for s in segmentos:
        print(
            f"  [{s.numero_segmento:02d}] Folio ~{s.folio_estimado:02d} "
            f"| {s.tipo_acto_procesal:<32} | {s.longitud_chars:>5} chars"
        )
    return segmentos


def paso_extraer(ruta_archivo: Path = RUTA_TRANSCRIPCION, forzar: bool = False):
    """Paso 2: Extracción de entidades con el LLM."""
    from pipeline.extractor import run_extraccion_completa

    print("\n" + "="*60)
    print(f"  PASO 2: EXTRACCIÓN CON LLM -> {ruta_archivo.name}")
    print("="*60)

    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n  ERROR: Variable GOOGLE_API_KEY no configurada.")
        print("  Configúrala en el archivo .env o en tu terminal:")
        print("    Linux/macOS: export GOOGLE_API_KEY='tu_clave_de_api'")
        print("    Windows:     $env:GOOGLE_API_KEY='tu_clave_de_api'")
        print("  Puedes obtener una en: https://aistudio.google.com/apikey")
        sys.exit(1)

    return run_extraccion_completa(
        ruta_transcripcion=ruta_archivo,
        ruta_salida_jsonl=RUTA_EXTRACCIONES,
        forzar_reextraccion=forzar,
    )


def paso_grafo(extracciones=None):
    """Paso 3: Construcción y exportación del grafo."""
    from pipeline.graph_builder import (
        extracciones_a_grafo_json,
        guardar_grafo_json,
        cargar_en_neo4j,
    )
    from ontology.models import ExtraccionFolio

    print("\n" + "="*60)
    print("  PASO 3: CONSTRUCCIÓN DEL GRAFO")
    print("="*60)

    # Si no vienen extracciones del paso anterior, las carga del JSONL
    if extracciones is None:
        if not RUTA_EXTRACCIONES.exists():
            print(f"\n  ERROR: No se encuentra {RUTA_EXTRACCIONES}")
            print("  Ejecuta primero: python run.py")
            sys.exit(1)

        extracciones = []
        with RUTA_EXTRACCIONES.open(encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    extracciones.append(ExtraccionFolio.model_validate_json(linea))

        print(f"\n  {len(extracciones)} extracciones cargadas desde {RUTA_EXTRACCIONES}")

    # Siempre exportar JSON de respaldo
    grafo = extracciones_a_grafo_json(extracciones)
    print(f"\n  Nodos por etiqueta:")
    for etiqueta, n in grafo["resumen"]["por_etiqueta"].items():
        print(f"    {etiqueta:<35} {n:>4}")
    print(f"    {'Aristas totales':<35} {grafo['resumen']['total_aristas']:>4}")
    guardar_grafo_json(grafo, RUTA_GRAFO)

    # Cargar en Neo4j si está configurado
    if os.environ.get("NEO4J_PASSWORD"):
        print("\n  Neo4j configurado -> cargando grafo ...")
        cargar_en_neo4j(extracciones)
    else:
        print(f"\n  Neo4j no configurado.")
        print(f"  Cuando tengas Neo4j Desktop corriendo, activa las variables")
        print(f"  NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD en el archivo .env")

    return grafo


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de extracción del Grafo de Conocimiento Histórico del Cusco"
    )
    parser.add_argument(
        "--solo-segmentar",
        action="store_true",
        help="Solo ejecuta el paso de segmentación (sin LLM)"
    )
    parser.add_argument(
        "--solo-grafo",
        action="store_true",
        help="Solo construye el grafo a partir de extracciones ya guardadas"
    )
    parser.add_argument(
        "--archivo",
        type=str,
        default=str(RUTA_TRANSCRIPCION),
        help="Ruta al archivo de transcripción dentro de corpus/ (por defecto: Transcripcion_CC_L14E18.txt)"
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Fuerza la reextracción completa con el LLM ignorando caché previa"
    )
    parser.add_argument(
        "--visualizar",
        action="store_true",
        help="Abre el visualizador web interactivo en el navegador (sin requerir Neo4j)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Calcula las estadísticas y métricas de calidad de construcción del grafo (KGCQ)"
    )
    args = parser.parse_args()
    ruta_archivo = Path(args.archivo)

    if args.stats:
        from stats.report import generar_reporte_completo
        generar_reporte_completo()
        return

    if args.visualizar:
        from visualizar import iniciar_visualizador
        iniciar_visualizador()
        return

    if args.solo_segmentar:
        paso_segmentar(ruta_archivo)
        return

    if args.solo_grafo:
        paso_grafo()
        return

    # Pipeline completo
    paso_segmentar(ruta_archivo)
    extracciones = paso_extraer(ruta_archivo, forzar=args.forzar)
    paso_grafo(extracciones)


if __name__ == "__main__":
    main()
