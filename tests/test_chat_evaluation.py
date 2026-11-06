"""Evaluación de recuperación y respuestas contra el expediente 18."""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pytest

from chat.local_chat import (
    LocalGraphChat,
    QuestionPlan,
    build_chat_from_environment,
    load_dotenv,
    retrieve_evidence,
)


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    question: str
    plan: QuestionPlan
    evidence_terms: tuple[str, ...]
    answer_terms: tuple[tuple[str, ...], ...]
    required_state: str | None = None


CASES = (
    EvaluationCase(
        "tinta-1806",
        "¿Qué ocurrió en el pueblo de Tinta en 1806?",
        QuestionPlan(intent="evento", termino="Tinta"),
        ("tinta", "1806"),
        (("tinta",), ("1806",), ("desmentido", "alegato")),
        "Desmentido_Falso",
    ),
    EvaluationCase(
        "principal-acusado",
        "¿Quién aparece como principal acusado o denunciado?",
        QuestionPlan(intent="acusado", termino="acusado"),
        ("chuquitapa", "denunciado"),
        (("chuquitapa",), ("acusado", "denunciado")),
        "Alegato_No_Comprobado",
    ),
    EvaluationCase(
        "tributarios-ocultos",
        "¿Qué se denunció sobre los tributarios ocultos?",
        QuestionPlan(intent="afirmacion", termino="tributarios"),
        ("tributarios", "Tinta"),
        (("tributarios",), ("tinta", "chuquitapa")),
        "Alegato_No_Comprobado",
    ),
    EvaluationCase(
        "manuel-huancachoque",
        "¿Qué le ocurrió a Manuel Huancachoque?",
        QuestionPlan(intent="actor", termino="Huancachoque"),
        ("huancachoque", "cárcel"),
        (("huancachoque",), ("cárcel", "carcel", "maltrat")),
    ),
    EvaluationCase(
        "ataque-orey",
        "¿Qué ocurrió con Miguel Orey?",
        QuestionPlan(intent="actor", termino="Orey"),
        ("orey",),
        (("orey",), ("alzamiento", "ataque", "pedrad", "palo")),
        None,
    ),
    EvaluationCase(
        "denunciante",
        "¿Quién denunció los tributarios ante la Real Hacienda?",
        QuestionPlan(intent="actor", termino="Manuel Huancachoque"),
        ("huancachoque", "tributari"),
        (("huancachoque",), ("real hacienda", "tributari")),
    ),
    EvaluationCase(
        "ayllu-tinta",
        "¿Qué relación aparece entre el Ayllu Tinta y los tributarios?",
        QuestionPlan(intent="lugar", termino="Ayllu Tinta"),
        ("ayllu", "tinta"),
        (("ayllu", "tinta"), ("tributari", "ocult")),
    ),
    EvaluationCase(
        "isidro-cano",
        "¿Qué declaró Isidro Cano?",
        QuestionPlan(intent="actor", termino="Isidro Cano"),
        ("cano", "sospech"),
        (("cano",), ("sospech", "traición", "traicion")),
        "Alegato_No_Comprobado",
    ),
    EvaluationCase(
        "resolucion-quejas",
        "¿Qué resolvió oficialmente el expediente sobre las quejas?",
        QuestionPlan(intent="afirmacion", termino="ResolucionOficial"),
        ("desmentido", "verdad"),
        (("queja",), ("desment", "no eran", "falso")),
        "Desmentido_Falso",
    ),
    EvaluationCase(
        "cuarenta-cuatro",
        "¿Cuántos tributarios fueron descubiertos en el Ayllu Tinta?",
        QuestionPlan(intent="afirmacion", termino="tributarios"),
        ("tributari", "tinta"),
        (("44", "cuarenta y cuatro"), ("ayllu", "tinta")),
        "Alegato_No_Comprobado",
    ),
)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _load_environment() -> None:
    load_dotenv(
        Path(__file__).resolve().parent.parent / ".env"
    )


@pytest.fixture(scope="session")
def graph_chat() -> LocalGraphChat:
    _load_environment()
    if not os.environ.get("NEO4J_PASSWORD"):
        pytest.skip("NEO4J_PASSWORD no está configurada")
    try:
        chat = build_chat_from_environment()
    except Exception as error:
        pytest.skip(f"Neo4j no está disponible: {error}")
    yield chat
    chat.driver.close()


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_corpus_case_retrieves_expected_evidence(graph_chat: LocalGraphChat, case: EvaluationCase):
    with graph_chat.driver.session() as session:
        evidence = retrieve_evidence(session, case.plan)

    assert evidence, f"No se recuperó evidencia para {case.name}"
    corpus = _normalize(" ".join(item.model_dump_json() for item in evidence))
    missing = [
        term
        for term in case.evidence_terms
        if _normalize(term) not in corpus
    ]
    assert not missing, f"Evidencia incompleta para {case.name}: {missing}"
    if case.required_state:
        assert any(
            item.estado_epistemologico == case.required_state for item in evidence
        )


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_live_llm_answer_is_grounded(
    graph_chat: LocalGraphChat, case: EvaluationCase
):
    if os.environ.get("RUN_LIVE_CHAT_EVAL") != "1":
        pytest.skip("Usa RUN_LIVE_CHAT_EVAL=1 para consultar Gemini")

    result = graph_chat.answer(case.question)
    assert result.evidencias, f"El LLM no recibió evidencia para {case.name}"
    answer = _normalize(result.respuesta)
    for alternatives in case.answer_terms:
        assert any(
            _normalize(term) in answer for term in alternatives
        ), f"Respuesta incompleta para {case.name}; falta uno de {alternatives}"
    if case.required_state:
        assert _normalize(case.required_state) in answer
