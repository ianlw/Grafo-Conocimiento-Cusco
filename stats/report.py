"""
Generador de Reportes de Calidad y Estadísticas del Grafo de Conocimiento (KGCQ)
================================================================================
Genera:
  1. Reporte formateado en consola (CLI).
  2. Archivo JSON estructurado ('data/estadisticas_calidad.json').
  3. Reporte en Markdown formal ('data/reporte_calidad.md') para investigación.
"""

import json
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from stats.metrics import EstadisticasCalidad, calcular_estadisticas_completas
DATA_DIR = ROOT_DIR / "data"
CORPUS_DIR = ROOT_DIR / "corpus"

RUTA_GRAFO = DATA_DIR / "grafo.json"
RUTA_EXTRACCIONES = DATA_DIR / "extracciones.jsonl"
RUTA_CORPUS = CORPUS_DIR / "Transcripcion_CC_L14E18.txt"

RUTA_SALIDA_JSON = DATA_DIR / "estadisticas_calidad.json"
RUTA_SALIDA_MD = DATA_DIR / "reporte_calidad.md"


def imprimir_reporte_consola(stats: EstadisticasCalidad) -> None:
    esq = stats.esquema
    anc = stats.anclaje
    can = stats.canonicalizacion
    epi = stats.epistemica
    top = stats.topologia
    kgcq = stats.calidad_kgcq

    print("\n" + "=" * 70)
    print("  EVALUACIÓN DE CALIDAD DE CONSTRUCCIÓN DEL GRAFO DE CONOCIMIENTO (KGCQ)")
    print("  Archivo Regional del Cusco — Fondo Intendencia (Causas Criminales)")
    print("=" * 70)

    # Resumen Ejecutivo
    print(f"\n[+] ÍNDICE COMPUESTO DE CALIDAD: {kgcq.score_global:.1f} / 100  (Grado: {kgcq.calificacion_letra})")
    print(f"    Diagnóstico: {kgcq.diagnostico}\n")

    # 1. Conformidad con el Metamodelo
    print("-" * 70)
    print("  1. CONFORMIDAD Y METAMODELO ONTOLÓGICO (RiC-O, CIDOC CRM, PROV-O, OHAC)")
    print("-" * 70)
    print(f"  • Total Nodos (|V|)           : {esq.total_nodos:>5}")
    for etiq, count in esq.nodos_por_etiqueta.items():
        print(f"      - :{etiq:<26} {count:>4} nodos")
    print(f"  • Total Aristas (|E|)         : {esq.total_aristas:>5}")
    for tipo, count in esq.aristas_por_tipo.items():
        print(f"      - [:{tipo:<24}] {count:>4} aristas")
    print(f"  • Integridad Referencial      : {esq.tasa_integridad_referencial * 100:>5.1f}% ({esq.aristas_rotas_referenciales} enlaces rotos)")
    print(f"  • Conformidad Dominio/Rango   : {esq.tasa_conformidad_metamodelo * 100:>5.1f}% ({esq.aristas_validas_metamodelo} válidas / {esq.aristas_invalidas_metamodelo} atípicas)")
    print(f"  • Nodos Aislados              : {esq.nodos_aislados:>5} (grado 0)")

    # 2. Fidelidad de Anclaje Textual
    print("\n" + "-" * 70)
    print("  2. FIDELIDAD DE ANCLAJE TEXTUAL Y EVIDENCIA (Grounding Veracity)")
    print("-" * 70)
    print(f"  • Citas Textuales Evaluadas   : {anc.total_citas_evaluadas:>5}")
    print(f"  • Coincidencias Exactas (100%): {anc.citas_coincidencia_exacta:>5} ({anc.tasa_coincidencia_exacta * 100:.1f}%)")
    print(f"  • Anclaje Alto (Fuzzy >= 85%) : {anc.citas_anclaje_alto:>5} ({anc.tasa_anclaje_alto * 100:.1f}%)")
    print(f"  • Anclaje Medio (70% - 84%)   : {anc.citas_anclaje_medio:>5} ({anc.tasa_anclaje_medio * 100:.1f}%)")
    print(f"  • Riesgo de Alucinación (< 70%): {anc.citas_riesgo_alucinacion:>5} ({anc.tasa_riesgo_alucinacion * 100:.1f}%)")
    print(f"  • Longitud Citas (caracteres) : Promedio {anc.longitud_promedio_chars:.0f} | Mín {anc.longitud_min_chars} | Máx {anc.longitud_max_chars}")
    print(f"  • Confianza Promedio LLM      : {anc.confianza_promedio_extractor:.2f} / 1.00")

    # 3. Canonicalización y Entidades
    print("\n" + "-" * 70)
    print("  3. CANONICALIZACIÓN Y RESOLUCIÓN DE ENTIDADES (SKOS prefLabel / altLabel)")
    print("-" * 70)
    print(f"  • Actores Canónicos Únicos    : {can.total_actores_canonicos:>5}")
    print(f"  • Actores con Variantes       : {can.actores_con_variantes:>5} ({can.total_variantes_ortograficas} grafías históricas documentadas)")
    print(f"  • Ratio Consolidación Superf. : {can.ratio_consolidadas_vs_superficie:.2f}x (variantes unificadas por actor)")
    print(f"  • Con Condición Socioétnica   : {can.actores_con_condicion_socioetnica:>5} ({can.tasa_condicion_socioetnica * 100:.1f}%)")
    print(f"  • Con Cargos Virreinales      : {can.actores_con_cargos_registrados:>5} ({can.tasa_cargos_registrados * 100:.1f}%)")

    # 4. Análisis Epistémico y Crítica de Fuentes
    print("\n" + "-" * 70)
    print("  4. ANÁLISIS EPISTÉMICO Y CRÍTICA DE FUENTES (OHAC + PROV-O)")
    print("-" * 70)
    print(f"  • Afirmaciones Reificadas     : {epi.total_afirmaciones:>5} (100% con declarante y cita obligatoria)")
    print("  • Distribución por Estado Epistemológico:")
    for estado, cnt in epi.distribucion_estados.items():
        print(f"      - {estado:<28} : {cnt:>3} ({cnt / epi.total_afirmaciones * 100:.1f}%)")
    print("  • Distribución por Tipo de Declaración:")
    for tdec, cnt in epi.distribucion_tipos_declaracion.items():
        print(f"      - {tdec:<28} : {cnt:>3} ({cnt / epi.total_afirmaciones * 100:.1f}%)")
    print(f"  • Relaciones de Contradicción : {epi.total_relaciones_contradiccion:>5} ([:CONTRADICE])")
    print(f"  • Relaciones de Ratificación  : {epi.total_relaciones_ratificacion:>5} ([:RATIFICA])")

    # 5. Topología y Red de Actores
    print("\n" + "-" * 70)
    print("  5. TOPOLOGÍA DE RED Y ACTORES HISTÓRICOS CLAVE")
    print("-" * 70)
    print(f"  • Densidad de la Red          : {top.densidad_grafo:.5f}")
    print(f"  • Grado Promedio              : {top.grado_promedio:.2f} conexiones/nodo")
    print(f"  • Componentes Conexas         : {top.total_componentes_conexas}")
    print(f"  • Cobertura Componente Gigante: {top.cobertura_componente_gigante * 100:.1f}% ({top.tamano_componente_gigante} nodos)")
    print("\n  • Top 5 Actores con Mayor Centralidad de Grado:")
    for idx, act in enumerate(top.top_actores_centralidad[:5], 1):
        cond = f" [{act.condicion}]" if act.condicion else ""
        print(f"     {idx}. {act.nombre:<26}{cond:<22} Conexiones: {act.grado:>3} (In: {act.grado_entrada}, Out: {act.grado_salida})")

    print("\n" + "=" * 70 + "\n")


def generar_markdown(stats: EstadisticasCalidad) -> str:
    esq = stats.esquema
    anc = stats.anclaje
    can = stats.canonicalizacion
    epi = stats.epistemica
    top = stats.topologia
    kgcq = stats.calidad_kgcq

    md = f"""# Evaluación de Calidad de Construcción del Grafo de Conocimiento (KGCQ)

**Caso de Estudio:** Expediente 18, Legajo 14 (1806), Serie Causas Criminales, Fondo Intendencia del Archivo Regional del Cusco (ARC).  
**Metodología:** Inspirada en la evaluación formal de grafos de conocimiento generados por LLMs (*Ontology-grounded Automatic Knowledge Graph Construction by LLM*, Feng et al., KDD 2024).

---

## 🏆 Resumen Ejecutivo del Índice KGCQ

| Métrica Global | Valor | Grado | Diagnóstico |
| :--- | :---: | :---: | :--- |
| **Índice Compuesto KGCQ** | **{kgcq.score_global:.1f} / 100** | **{kgcq.calificacion_letra}** | {kgcq.diagnostico} |

### Desglose de Sub-puntuaciones
* **Conformidad con el Metamodelo (25%):** `{kgcq.subscores['conformidad_metamodelo']:.1f}%`
* **Fidelidad de Anclaje Textual (30%):** `{kgcq.subscores['fidelidad_anclaje_textual']:.1f}%`
* **Conectividad Estructural (20%):** `{kgcq.subscores['conectividad_estructural']:.1f}%`
* **Canonicalización y Normalización SKOS (15%):** `{kgcq.subscores['canonicalizacion_skos']:.1f}%`
* **Completitud y Reificación Epistémica (10%):** `{kgcq.subscores['completitud_epistemica']:.1f}%`

---

## 1. Conformidad con el Metamodelo Ontológico

Evaluación del cumplimiento de las restricciones ontológicas basadas en **RiC-O**, **CIDOC CRM (ISO 21127)**, **PROV-O** y **OHAC**:

| Dimensión | Conteo | Porcentaje |
| :--- | :---: | :---: |
| **Nodos Totales ($|V|$)** | **{esq.total_nodos}** | 100.0% |
| **Aristas Totales ($|E|$)** | **{esq.total_aristas}** | 100.0% |
| **Integridad Referencial** | {esq.total_aristas - esq.aristas_rotas_referenciales} / {esq.total_aristas} | **{esq.tasa_integridad_referencial * 100:.1f}%** |
| **Conformidad Dominio / Rango** | {esq.aristas_validas_metamodelo} / {esq.total_aristas - esq.aristas_rotas_referenciales} | **{esq.tasa_conformidad_metamodelo * 100:.1f}%** |
| **Nodos Aislados (Grado = 0)** | {esq.nodos_aislados} | {esq.nodos_aislados / esq.total_nodos * 100:.1f}% |

### Distribución de Nodos por Clase Ontológica
"""
    for etiq, count in esq.nodos_por_etiqueta.items():
        md += f"* **`:{etiq}`**: {count} ({count / esq.total_nodos * 100:.1f}%)\n"

    md += """
### Distribución de Aristas por Tipo de Relación
"""
    for tipo, count in esq.aristas_por_tipo.items():
        md += f"* **`[:{tipo}]`**: {count} ({count / esq.total_aristas * 100:.1f}%)\n"

    md += f"""
---

## 2. Fidelidad de Anclaje Textual y Verificación de Citas (Grounding Veracity)

En concordancia con el principio de *ontology grounding* para mitigar alucinaciones de LLMs, cada afirmación testimonial extraída se valida contra el texto paleográfico original:

| Nivel de Anclaje | Citas | Porcentaje | Interpretación |
| :--- | :---: | :---: | :--- |
| **Coincidencia Exacta (100%)** | **{anc.citas_coincidencia_exacta}** | **{anc.tasa_coincidencia_exacta * 100:.1f}%** | Subcadena textual idéntica al manuscrito original. |
| **Anclaje Alto (>= 85%)** | **{anc.citas_anclaje_alto}** | **{anc.tasa_anclaje_alto * 100:.1f}%** | Cita fidedigna con variaciones menores de espaciado/puntuación paleográfica. |
| **Anclaje Medio (70% - 84%)** | **{anc.citas_anclaje_medio}** | **{anc.tasa_anclaje_medio * 100:.1f}%** | Cita con ligera paráfrasis o elisión textual. |
| **Riesgo de Alucinación (< 70%)** | **{anc.citas_riesgo_alucinacion}** | **{anc.tasa_riesgo_alucinacion * 100:.1f}%** | Testimonio no respaldado fehacientemente en la fuente. |

* **Total de Citas Evaluadas:** {anc.total_citas_evaluadas}
* **Longitud Promedio de Evidencia:** {anc.longitud_promedio_chars:.1f} caracteres (Rango: [{anc.longitud_min_chars} - {anc.longitud_max_chars}])
* **Confianza Promedio del Extractor LLM:** {anc.confianza_promedio_extractor:.2f} / 1.00

---

## 3. Canonicalización y Desambiguación de Entidades (SKOS)

Evaluación del tratamiento de la inestabilidad ortográfica colonial andina:

* **Actores Canónicos Registrados:** {can.total_actores_canonicos}
* **Actores con Variantes Históricas (`altLabel`):** {can.actores_con_variantes} ({can.total_variantes_ortograficas} grafías registradas)
* **Factor de Consolidación de Superficie:** **{can.ratio_consolidadas_vs_superficie:.2f}x** (unificación de variantes como *Huancachoque*, *Guancachoque*, *Mancachoque* en una sola entidad).
* **Tasa de Identificación Socioétnica:** **{can.tasa_condicion_socioetnica * 100:.1f}%** (atribución explícita de *Indio Originario*, *Noble Cacique*, *Español Vecino*, etc.).
* **Tasa de Identificación de Cargos/Oficios:** **{can.tasa_cargos_registrados * 100:.1f}%** (*Cacique Recaudador*, *Sargento de Milicias*, *Subdelegado*, etc.).

---

## 4. Análisis Epistémico y Crítica de Fuentes (OHAC)

Estructuración de testimonios y reificación para evitar el sesgo factual ingenuo:

* **Total Afirmaciones Reificadas:** {epi.total_afirmaciones}
* **Tasa de Reificación con Evidencia Obligatoria:** **{epi.tasa_reificacion_epistemica * 100:.1f}%**

### Distribución por Estado Epistemológico
"""
    for estado, cnt in epi.distribucion_estados.items():
        md += f"* **`{estado}`**: {cnt} ({cnt / epi.total_afirmaciones * 100:.1f}%)\n"

    md += """
### Distribución por Tipo de Declaración
"""
    for tdec, cnt in epi.distribucion_tipos_declaracion.items():
        md += f"* **`{tdec}`**: {cnt} ({cnt / epi.total_afirmaciones * 100:.1f}%)\n"

    md += f"""
* **Relaciones de Contradicción (`[:CONTRADICE]`):** {epi.total_relaciones_contradiccion}
* **Relaciones de Ratificación (`[:RATIFICA]`):** {epi.total_relaciones_ratificacion}

---

## 5. Topología de Red y Actores Históricos Centrales

* **Densidad del Grafo:** `{top.densidad_grafo:.5f}`
* **Grado Promedio:** `{top.grado_promedio:.2f}` aristas por nodo
* **Componentes Conexas:** `{top.total_componentes_conexas}` (Componente Gigante agrupa al `{top.cobertura_componente_gigante * 100:.1f}%` de los nodos)

### Ranking de Centralidad de Grado (Top 10 Actores Clave)

| # | Actor | Condición / Tipo | Grado Total | Conexiones Entrantes | Conexiones Salientes |
| :-: | :--- | :--- | :-: | :-: | :-: |
"""
    for idx, act in enumerate(top.top_actores_centralidad, 1):
        cond = act.condicion if act.condicion else "No especificada"
        md += f"| {idx} | **{act.nombre}** | {cond} | {act.grado} | {act.grado_entrada} | {act.grado_salida} |\n"

    md += """
---
*Generado automáticamente por el motor de estadísticas KGCQ de Grafo de Conocimiento Histórico del Cusco.*
"""
    return md


def generar_reporte_completo(
    ruta_grafo: Path = RUTA_GRAFO,
    ruta_extracciones: Path = RUTA_EXTRACCIONES,
    ruta_corpus: Path = RUTA_CORPUS,
    ruta_salida_json: Path = RUTA_SALIDA_JSON,
    ruta_salida_md: Path = RUTA_SALIDA_MD,
) -> EstadisticasCalidad:
    """Calcula estadísticas, imprime en consola y guarda respaldos en JSON y Markdown."""
    stats = calcular_estadisticas_completas(
        ruta_grafo=ruta_grafo,
        ruta_extracciones=ruta_extracciones,
        ruta_corpus=ruta_corpus,
    )

    imprimir_reporte_consola(stats)

    # Exportar JSON
    ruta_salida_json.parent.mkdir(parents=True, exist_ok=True)
    with ruta_salida_json.open("w", encoding="utf-8") as f:
        json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"[stats] Estadísticas exportadas en JSON: {ruta_salida_json}")

    # Exportar Markdown
    ruta_salida_md.parent.mkdir(parents=True, exist_ok=True)
    md_content = generar_markdown(stats)
    ruta_salida_md.write_text(md_content, encoding="utf-8")
    print(f"[stats] Reporte analítico exportado en Markdown: {ruta_salida_md}")

    return stats


if __name__ == "__main__":
    generar_reporte_completo()
