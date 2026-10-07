from chat.local_chat import Evidence, QuestionPlan, retrieve_evidence


class FakeRecord:
    def __init__(self, values):
        self.values = values

    def data(self):
        return self.values


class FakeSession:
    def __init__(self):
        self.query = None
        self.parameters = None

    def run(self, query, **parameters):
        self.query = query
        self.parameters = parameters
        return [
            FakeRecord(
                {
                    "fuente_id": "exp_f01",
                    "folio": 1,
                    "expediente": 18,
                    "declarante": "Isidro Cano",
                    "tipo_declaracion": "Sospecha",
                    "estado_epistemologico": "Alegato_No_Comprobado",
                    "cita": "cita textual válida",
                    "contexto": "Isidro Cano",
                }
            )
        ]


def test_retrieve_evidence_uses_parameterized_read_query():
    session = FakeSession()

    evidence = retrieve_evidence(
        session,
        QuestionPlan(intent="actor", termino="Cano"),
    )

    assert len(evidence) == 1
    assert isinstance(evidence[0], Evidence)
    assert evidence[0].estado_epistemologico == "Alegato_No_Comprobado"
    assert session.parameters == {"termino": "Cano", "limite": 20}
    assert "MERGE" not in session.query
    assert "DELETE" not in session.query
    assert "DROP" not in session.query


def test_question_plan_rejects_empty_search_term():
    from pydantic import ValidationError

    try:
        QuestionPlan(intent="actor", termino="")
    except ValidationError:
        pass
    else:
        raise AssertionError("Empty search terms must be rejected")


def test_affirmation_query_can_find_declarante():
    session = FakeSession()

    evidence = retrieve_evidence(
        session,
        QuestionPlan(intent="afirmacion", termino="Cano"),
    )

    assert len(evidence) == 1
    assert "declarante.nombre" in session.query


def test_accused_query_uses_testimonial_roles():
    session = FakeSession()

    evidence = retrieve_evidence(
        session,
        QuestionPlan(intent="acusado", termino="acusado"),
    )

    assert len(evidence) == 1
    assert "ROL_EN_EVENTO" in session.query
    assert "DELETE" not in session.query


def test_event_query_searches_connected_places_and_dates():
    session = FakeSession()

    evidence = retrieve_evidence(
        session,
        QuestionPlan(intent="evento", termino="Tinta"),
    )

    assert len(evidence) == 1
    assert "OCURRE_EN" in session.query
    assert "fecha_alegada" in session.query
