"""
Tests Unitarios para el Módulo de Estadísticas y Calidad del Grafo (KGCQ)
========================================================================
Valida el cálculo de métricas de esquema, anclaje textual, canonicalización,
topología e índice compuesto KGCQ.
"""

from pathlib import Path
import pytest

from stats.metrics import EvaluadorCalidadGrafo, calcular_estadisticas_completas

BASE_DIR = Path(__file__).resolve().parent.parent
RUTA_GRAFO = BASE_DIR / "data" / "grafo.json"
RUTA_EXTRACCIONES = BASE_DIR / "data" / "extracciones.jsonl"
RUTA_CORPUS = BASE_DIR / "corpus" / "Transcripcion_CC_L14E18.txt"


@pytest.fixture
def evaluador():
    return EvaluadorCalidadGrafo(
        ruta_grafo_json=RUTA_GRAFO,
        ruta_extracciones_jsonl=RUTA_EXTRACCIONES,
        ruta_corpus_txt=RUTA_CORPUS,
    )


def test_evaluacion_esquema_e_integridad(evaluador):
    m = evaluador.evaluar_esquema()
    assert m.total_nodos == 259
    assert m.total_aristas == 574
    # Integridad referencial perfecta (0 enlaces rotos tras resolución de lugares)
    assert m.aristas_rotas_referenciales == 0
    assert m.tasa_integridad_referencial == 1.0
    # Conformidad de dominio y rango
    assert m.tasa_conformidad_metamodelo == 1.0
    assert m.nodos_aislados == 0
    assert "Actor" in m.nodos_por_etiqueta
    assert "AfirmacionHistorica" in m.nodos_por_etiqueta


def test_evaluacion_anclaje_textual_veracity(evaluador):
    m = evaluador.evaluar_anclaje()
    assert m.total_citas_evaluadas > 0
    # Más del 90% de las citas tienen anclaje alto (>= 85% similitud fuzzy o exactas)
    assert m.tasa_anclaje_alto >= 0.90
    # Riesgo de alucinación debe ser nulo o menor a 5%
    assert m.tasa_riesgo_alucinacion <= 0.05
    assert m.longitud_promedio_chars >= 50
    assert m.score_fidelidad_anclaje >= 0.85


def test_evaluacion_canonicalizacion_skos(evaluador):
    m = evaluador.evaluar_canonicalizacion()
    assert m.total_actores_canonicos > 0
    assert m.actores_con_variantes > 0
    assert m.total_variantes_ortograficas > 0
    assert m.ratio_consolidadas_vs_superficie > 1.0
    assert m.tasa_condicion_socioetnica > 0.40


def test_evaluacion_topologia_y_centralidad(evaluador):
    m = evaluador.evaluar_topologia()
    assert m.densidad_grafo > 0.0
    assert m.grado_promedio > 2.0
    assert m.total_componentes_conexas >= 1
    # Componente gigante debe abarcar la gran mayoría o totalidad del grafo
    assert m.cobertura_componente_gigante >= 0.90
    assert len(m.top_actores_centralidad) > 0
    # Los actores principales del litigio deben aparecer en los primeros puestos
    nombres_top = [a.nombre for a in m.top_actores_centralidad]
    assert any("Huancachoque" in n for n in nombres_top)
    assert any("Chuquitapa" in n for n in nombres_top)


def test_indice_compuesto_kgcq(evaluador):
    stats = evaluador.ejecutar()
    kgcq = stats.calidad_kgcq
    assert 0.0 <= kgcq.score_global <= 100.0
    assert kgcq.score_global >= 85.0
    assert kgcq.calificacion_letra in {"A+", "A"}
    for sub, val in kgcq.subscores.items():
        assert 0.0 <= val <= 100.0
