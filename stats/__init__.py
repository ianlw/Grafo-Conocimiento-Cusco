"""
Módulo de Estadísticas y Evaluación de Calidad de Construcción del Grafo (KGCQ)
================================================================================
Inspirado en la metodología de 'Ontology-grounded Automatic Knowledge Graph
Construction by LLM' (Feng, Wu, Meng, KDD 2024).

Evalúa:
  1. Conformidad con el Esquema Ontológico (RiC-O, CIDOC CRM, PROV-O, SKOS, OHAC)
  2. Fidelidad de Anclaje Textual (Grounding & Evidence Veracity)
  3. Canonicalización y Resolución de Entidades (SKOS)
  4. Balance Epistémico y Crítica de Fuentes (OHAC)
  5. Topología y Conectividad del Grafo
  6. Índice Compuesto de Calidad de Construcción (KGCQ Index)
"""

from stats.metrics import calcular_estadisticas_completas, EvaluadorCalidadGrafo
from stats.report import generar_reporte_completo, imprimir_reporte_consola

__all__ = [
    "calcular_estadisticas_completas",
    "EvaluadorCalidadGrafo",
    "generar_reporte_completo",
    "imprimir_reporte_consola",
]
