"""Consulta local de Neo4j con Gemini y respuestas fundamentadas.

El LLM clasifica la pregunta y redacta la respuesta. Las consultas Neo4j
son fijas y parametrizadas para mantener el acceso en solo lectura.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from neo4j import Driver, GraphDatabase
from pydantic import BaseModel, Field


Intent = Literal["actor", "acusado", "afirmacion", "evento", "lugar", "general"]
MAX_EVIDENCE = 20


class QuestionPlan(BaseModel):
    intent: Intent
    termino: str = Field(min_length=1, max_length=200)


class Evidence(BaseModel):
    fuente_id: str
    folio: int | None = None
    expediente: int | None = None
    declarante: str | None = None
    tipo_declaracion: str | None = None
    estado_epistemologico: str | None = None
    cita: str | None = None
    contexto: str


class ChatResponse(BaseModel):
    respuesta: str
    evidencias: list[Evidence]
    advertencia: str | None = None


PLANNER_SYSTEM = """Eres un clasificador de preguntas sobre un grafo histórico.
Devuelve solo JSON válido con esta forma:
{"intent":"actor|acusado|afirmacion|evento|lugar|general","termino":"texto de búsqueda"}

Usa actor para preguntas sobre una persona, institución, ayllu o grupo.
Usa acusado para preguntas sobre el principal acusado, denunciado, agresor o responsable.
Usa afirmacion para acusaciones, testimonios, sospechas o estados de verdad.
Usa evento para hechos institucionales o eventos narrados.
Usa lugar para preguntas sobre ubicaciones.
Usa general cuando no puedas identificar una entidad concreta.
No inventes nombres. Conserva el término principal de la pregunta."""

ANSWER_SYSTEM = """Responde en español usando solo la evidencia entregada.
No inventes hechos ni completes datos ausentes.
Distingue siempre Alegato_No_Comprobado, Confirmado_Oficial,
Desmentido_Falso y En_Disputa.
Una sospecha o acusación no es un hecho confirmado.
Si la evidencia no responde la pregunta, dilo claramente.
Menciona folio, expediente y cita literal cuando estén disponibles.
No afirmes que consultaste fuentes que no aparecen en la evidencia."""


def _records_to_evidence(records: list[dict[str, Any]]) -> list[Evidence]:
    return [Evidence.model_validate(record) for record in records[:MAX_EVIDENCE]]


def _rows_to_dicts(result: Any) -> list[dict[str, Any]]:
    return [record.data() for record in result]


def retrieve_evidence(session: Any, plan: QuestionPlan) -> list[Evidence]:
    """Recupera contexto mediante consultas Cypher fijas y de solo lectura."""
    queries: dict[str, str] = {
        "actor": """
            MATCH (a:Actor)
            WHERE toLower(a.nombre) CONTAINS toLower($termino)
               OR any(v IN coalesce(a.variantes, []) WHERE
                      toLower(v) CONTAINS toLower($termino))
            OPTIONAL MATCH (a)-[:DECLARO]->(af:AfirmacionHistorica)
            OPTIONAL MATCH (af)-[:EXTRAIDO_DE]->(af_f:FuenteArchivistica)
            OPTIONAL MATCH (a)-[:MENCIONADO_EN]->(mention_f:FuenteArchivistica)
            WITH a, af, coalesce(af_f, mention_f) AS f
            WHERE f IS NOT NULL
            RETURN f.id AS fuente_id, f.folio AS folio, f.expediente AS expediente,
                   a.nombre AS declarante,
                   af.tipo_declaracion AS tipo_declaracion,
                   af.estado AS estado_epistemologico,
                   af.cita AS cita,
                   coalesce(a.nombre, '') AS contexto
            LIMIT $limite
        """,
        "acusado": """
            MATCH (a:Actor)-[r:ROL_EN_EVENTO]->(e:EventoTestimoniado)
            WHERE toLower(coalesce(r.rol, '')) CONTAINS 'acus'
               OR toLower(coalesce(r.rol, '')) CONTAINS 'denunci'
               OR toLower(coalesce(r.rol, '')) CONTAINS 'agresor'
               OR toLower(coalesce(r.rol, '')) CONTAINS 'respons'
            OPTIONAL MATCH (af:AfirmacionHistorica)-[:DESCRIBE_EVENTO]->(e)
            OPTIONAL MATCH (af)-[:EXTRAIDO_DE]->(f:FuenteArchivistica)
            WITH a, r, af, f
            WHERE f IS NOT NULL
            RETURN f.id AS fuente_id, f.folio AS folio, f.expediente AS expediente,
                   a.nombre AS declarante,
                   af.tipo_declaracion AS tipo_declaracion,
                   af.estado AS estado_epistemologico,
                   af.cita AS cita,
                   coalesce(a.nombre, '') + ' — rol: ' + coalesce(r.rol, '') AS contexto
            ORDER BY CASE
                WHEN toLower(coalesce(r.rol, '')) CONTAINS 'denunciado' THEN 0
                WHEN toLower(coalesce(r.rol, '')) CONTAINS 'acusado' THEN 1
                ELSE 2
            END
            LIMIT $limite
        """,
        "afirmacion": """
            MATCH (af:AfirmacionHistorica)
            OPTIONAL MATCH (declarante:Actor)-[:DECLARO]->(af)
            OPTIONAL MATCH (af)-[:EXTRAIDO_DE]->(f:FuenteArchivistica)
            WHERE toLower(coalesce(af.cita, '')) CONTAINS toLower($termino)
               OR toLower(coalesce(af.tipo_declaracion, '')) CONTAINS toLower($termino)
               OR toLower(coalesce(af.estado, '')) CONTAINS toLower($termino)
               OR toLower(coalesce(declarante.nombre, '')) CONTAINS toLower($termino)
            WITH af, declarante, f
            WHERE f IS NOT NULL
            RETURN f.id AS fuente_id, f.folio AS folio, f.expediente AS expediente,
                   declarante.nombre AS declarante,
                   af.tipo_declaracion AS tipo_declaracion,
                   af.estado AS estado_epistemologico,
                   af.cita AS cita,
                   coalesce(af.tipo_declaracion, '') AS contexto
            LIMIT $limite
        """,
        "evento": """
            MATCH (e)
            WHERE (e:EventoInstitucional OR e:EventoTestimoniado)
            OPTIONAL MATCH (e)-[:OCURRE_EN]-(l:Lugar)
            OPTIONAL MATCH (e)-[:DOCUMENTADO_EN]->(institutional_f:FuenteArchivistica)
            OPTIONAL MATCH (e)<-[:DESCRIBE_EVENTO]-(af:AfirmacionHistorica)
                          -[:EXTRAIDO_DE]->(testimonial_f:FuenteArchivistica)
            WITH e, l, af, coalesce(institutional_f, testimonial_f) AS f
            WHERE (
                toLower(coalesce(e.tipo_evento, '')) CONTAINS toLower($termino)
                OR toLower(coalesce(e.fecha_alegada, '')) CONTAINS toLower($termino)
                OR toLower(coalesce(l.nombre, '')) CONTAINS toLower($termino)
                OR toLower(coalesce(l.nombre, '')) CONTAINS
                   replace(toLower($termino), 'pueblo de ', '')
            ) AND f IS NOT NULL
            RETURN f.id AS fuente_id, f.folio AS folio, f.expediente AS expediente,
                   null AS declarante,
                   af.tipo_declaracion AS tipo_declaracion,
                   af.estado AS estado_epistemologico,
                   af.cita AS cita,
                   coalesce(e.tipo_evento, '') +
                   CASE WHEN l.nombre IS NOT NULL THEN ' en ' + l.nombre ELSE '' END +
                   CASE WHEN e.fecha_alegada IS NOT NULL THEN
                       ' (' + e.fecha_alegada + ')' ELSE '' END AS contexto
            LIMIT $limite
        """,
        "lugar": """
            MATCH (l:Lugar)
            WHERE toLower(coalesce(l.nombre, '')) CONTAINS toLower($termino)
            OPTIONAL MATCH (l)-[:MENCIONADO_EN]-(f:FuenteArchivistica)
            RETURN f.id AS fuente_id, f.folio AS folio, f.expediente AS expediente,
                   null AS declarante, null AS tipo_declaracion,
                   null AS estado_epistemologico, null AS cita,
                   coalesce(l.nombre, '') AS contexto
            LIMIT $limite
        """,
        "general": """
            MATCH (n)-[]-(f:FuenteArchivistica)
            RETURN f.id AS fuente_id, f.folio AS folio, f.expediente AS expediente,
                   null AS declarante, null AS tipo_declaracion,
                   null AS estado_epistemologico, null AS cita,
                   coalesce(n.nombre, n.tipo_evento, n.descripcion, '') AS contexto
            LIMIT $limite
        """,
    }
    result = session.run(
        queries[plan.intent],
        termino=plan.termino,
        limite=MAX_EVIDENCE,
    )
    return _records_to_evidence(_rows_to_dicts(result))


class LocalGraphChat:
    """Orquesta planificación Gemini, recuperación Neo4j y respuesta Gemini."""

    def __init__(
        self,
        driver: Driver,
        client: Any,
        model: str = "gemini-3.1-flash-lite",
        fallback_model: str = "gemini-flash-lite-latest",
    ) -> None:
        self.driver = driver
        self.client = client
        self.model = model
        self.fallback_model = fallback_model
        self.used_fallback = False

    def _generate_content(self, **kwargs: Any) -> Any:
        from google.genai.errors import ServerError

        try:
            return self.client.models.generate_content(model=self.model, **kwargs)
        except ServerError as error:
            if (
                self.model == self.fallback_model
            ):
                raise
            self.used_fallback = True
            return self.client.models.generate_content(
                model=self.fallback_model,
                **kwargs,
            )

    def plan_question(self, question: str) -> QuestionPlan:
        from google.genai import types

        response = self._generate_content(
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM,
                temperature=0.0,
                response_mime_type="application/json",
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        return QuestionPlan.model_validate(json.loads(response.text))

    def answer(self, question: str) -> ChatResponse:
        from google.genai import types

        self.used_fallback = False
        plan = self.plan_question(question)
        with self.driver.session() as session:
            evidence = retrieve_evidence(session, plan)

        if not evidence:
            return ChatResponse(
                respuesta="No encontré evidencia coincidente en el grafo.",
                evidencias=[],
                advertencia=self._warning(
                    "La consulta no produjo resultados; no se generó una conclusión histórica."
                ),
            )

        context = json.dumps(
            [item.model_dump(exclude_none=True) for item in evidence],
            ensure_ascii=False,
            indent=2,
        )
        response = self._generate_content(
            contents=f"Pregunta:\n{question}\n\nEvidencia del grafo:\n{context}",
            config=types.GenerateContentConfig(
                system_instruction=ANSWER_SYSTEM,
                temperature=0.1,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        return ChatResponse(
            respuesta=response.text.strip(),
            evidencias=evidence,
            advertencia=self._warning(),
        )

    def _warning(self, message: str | None = None) -> str | None:
        fallback_message = (
            f"El modelo principal no estaba disponible; se usó {self.fallback_model}."
        )
        if message and self.used_fallback:
            return f"{message} {fallback_message}"
        return fallback_message if self.used_fallback else message


def build_chat_from_environment() -> LocalGraphChat:
    from google import genai

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not password:
        raise EnvironmentError("NEO4J_PASSWORD no está configurada.")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY no está configurada.")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return LocalGraphChat(
        driver,
        genai.Client(api_key=api_key, http_options={"api_version": "v1beta"}),
        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        fallback_model=os.environ.get(
            "GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest"
        ),
    )


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    chat = build_chat_from_environment()
    print("Chat local conectado. Escribe 'salir' para terminar.")
    try:
        while True:
            question = input("\nTú: ").strip()
            if question.lower() in {"salir", "exit", "quit"}:
                break
            if not question:
                continue
            result = chat.answer(question)
            print(f"\nAsistente: {result.respuesta}")
            if result.advertencia:
                print(f"Advertencia: {result.advertencia}")
            for evidence in result.evidencias:
                print(
                    f"\n[Folio {evidence.folio}, expediente {evidence.expediente}] "
                    f"{evidence.estado_epistemologico or 'Sin estado'}"
                )
                if evidence.cita:
                    print(f"Cita: {evidence.cita}")
    finally:
        chat.driver.close()


if __name__ == "__main__":
    main()
