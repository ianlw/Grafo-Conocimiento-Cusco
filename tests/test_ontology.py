"""
Tests de Validación Ontológica - Ontología Histórica del Archivo del Cusco (OHAC)
Verifica la consistencia del modelo frente al texto real del Legajo 14, Expediente 18 (1806).
"""

import pytest
from pydantic import ValidationError

from ontology.models import (
    UnidadArchivistica,
    Lugar,
    ObjetoOBien,
    ActorHistorico,
    Participacion,
    EventoHistorico,
    AfirmacionHistorica,
    ExtraccionFolio,
)
from ontology.standards import (
    RICO_MAPPING,
    CIDOC_MAPPING,
    PROV_MAPPING,
    SKOS_MAPPING,
    OHAC_EXTENSIONS,
)


def test_standards_definitions_present():
    """Comprueba que todos los mapeos de estándares estén cargados correctamente."""
    assert "RecordSet" in RICO_MAPPING
    assert "E21_Person" in CIDOC_MAPPING
    assert "wasDerivedFrom" in PROV_MAPPING
    assert "prefLabel" in SKOS_MAPPING
    assert "Ayllu" in OHAC_EXTENSIONS
    assert "AfirmacionHistorica" in OHAC_EXTENSIONS


def test_instanciacion_folio_01_caso_isidro_cano():
    """
    Simula la extracción estructurada del Folio 1:
    Isidro Cano afirma sospecha de que Chuquitapa ordenó el tumulto contra Huancachoque.
    """
    unidad = UnidadArchivistica(
        fondo="Intendencia",
        serie="Causas Criminales",
        legajo=14,
        expediente=18,
        folio=1,
        fragmento_id="exp18_f01_frag01",
        texto_original="Yo el sargento Don Isidro Cano de esta compañía de Tinta... Es cierto que al denunciante Guancachoque lo estropearon sus enemigos..."
    )

    actor_cano = ActorHistorico(
        id_canonico="persona_isidro_cano",
        nombre_principal="Isidro Cano",
        variantes_ortograficas=["Ysidro Cano"],
        tipo_actor="Persona",
        condicion_socioetnica="EspanolVecino",
        cargos_mencionados=["Sargento de Milicias de Tinta"]
    )

    actor_huancachoque = ActorHistorico(
        id_canonico="persona_manuel_huancachoque",
        nombre_principal="Manuel Huancachoque",
        variantes_ortograficas=["Manuel Guancachoque", "Manuel Mancachoque", "Manuel Huamanchoque"],
        tipo_actor="Persona",
        condicion_socioetnica="IndioOriginario",
        cargos_mencionados=["Soldado de milicias"]
    )

    actor_chuquitapa = ActorHistorico(
        id_canonico="persona_andres_chuquitapa",
        nombre_principal="Andrés Chuquitapa",
        variantes_ortograficas=["Andres Choquetapa"],
        tipo_actor="Persona",
        condicion_socioetnica="Noble_Cacique",
        cargos_mencionados=["Cacique del Ayllu Tinta", "Recaudador de Reales Tributos"]
    )

    lugar_tinta = Lugar(
        id="lugar_pueblo_tinta",
        nombre_mencionado="Pueblo de Tinta",
        tipo_lugar="Pueblo",
        jurisdiccion_superior="Partido de Tinta, Intendencia del Cusco"
    )

    evento_agresion = EventoHistorico(
        id="evento_agresion_huancachoque_f01",
        tipo_evento="Agresion_Fisica",
        categoria_tematica="Judicial_Conflictos",
        fecha_mencionada="Primero de agosto de 1806",
        lugar="lugar_pueblo_tinta",
        participantes=[
            Participacion(actor_id="persona_manuel_huancachoque", rol="Victima"),
            Participacion(actor_id="persona_andres_chuquitapa", rol="Sospechoso_Autor_Intelectual")
        ]
    )

    afirmacion_cano = AfirmacionHistorica(
        id="afirmacion_cano_folio_01",
        declarante_id="persona_isidro_cano",
        tipo_declaracion="Sospecha",
        estado_epistemologico="Alegato_No_Comprobado",
        evento_descrito=evento_agresion,
        cita_textual_evidencia="llevamos hasta hoy dia suspecha de la traicion de la orden del dicho Chuquitapa",
        folio=1,
        expediente_id="exp_ccc_14_18",
        confianza_extraccion=0.98
    )

    extraccion = ExtraccionFolio(
        unidad_archivistica=unidad,
        actores=[actor_cano, actor_huancachoque, actor_chuquitapa],
        lugares=[lugar_tinta],
        afirmaciones=[afirmacion_cano]
    )

    assert extraccion.unidad_archivistica.folio == 1
    assert len(extraccion.actores) == 3
    assert extraccion.afirmaciones[0].tipo_declaracion == "Sospecha"
    assert extraccion.afirmaciones[0].estado_epistemologico == "Alegato_No_Comprobado"
    assert "Manuel Mancachoque" in extraccion.actores[1].variantes_ortograficas


def test_resolucion_oficial_y_contradiccion():
    """
    Verifica que la resolución del Subdelegado Pedro de la Mata pueda enlazar
    y contradecir directamente las afirmaciones iniciales de agresión.
    """
    evento_falsedad = EventoHistorico(
        id="evento_dictamen_falsedad_queja",
        tipo_evento="ResolucionJudicial",
        categoria_tematica="Judicial_Conflictos",
        fecha_mencionada="Noviembre 8 de 1806",
        lugar="lugar_sicuani",
        participantes=[
            Participacion(actor_id="persona_pedro_de_la_mata", rol="Juez_Subdelegado"),
            Participacion(actor_id="persona_manuel_huancachoque", rol="Querellante_Apercibido")
        ]
    )

    afirmacion_dictamen = AfirmacionHistorica(
        id="afirmacion_dictamen_subdelegado_f30",
        declarante_id="persona_pedro_de_la_mata",
        tipo_declaracion="ResolucionOficial",
        estado_epistemologico="Confirmado_Oficial",
        evento_descrito=evento_falsedad,
        cita_textual_evidencia="fueron hechos por el mismo Guancachoque haciéndolos firmar a los sujetos que los subscriben sin saber lo más de sus contenidos",
        folio=30,
        expediente_id="exp_ccc_14_18",
        contradice_afirmacion_ids=["afirmacion_cano_folio_01"]
    )

    assert afirmacion_dictamen.estado_epistemologico == "Confirmado_Oficial"
    assert "afirmacion_cano_folio_01" in afirmacion_dictamen.contradice_afirmacion_ids


def test_regla_de_oro_cita_textual_obligatoria():
    """
    Regla fundamental: Una afirmación histórica NO puede existir sin cita textual
    de evidencia que acredite su procedencia (prov:wasDerivedFrom).
    """
    evento = EventoHistorico(
        id="evento_test",
        tipo_evento="Denuncia",
        categoria_tematica="Judicial_Conflictos"
    )

    # Caso 1: Cita vacía o demasiado corta
    with pytest.raises(ValidationError):
        AfirmacionHistorica(
            id="afirmacion_sin_cita",
            declarante_id="persona_isidro_cano",
            tipo_declaracion="Acusacion",
            evento_descrito=evento,
            cita_textual_evidencia="corta",  # Menos de 10 caracteres
            folio=1,
            expediente_id="exp_ccc_14_18"
        )

    # Caso 2: Cita con solo espacios en blanco
    with pytest.raises(ValidationError):
        AfirmacionHistorica(
            id="afirmacion_espacios",
            declarante_id="persona_isidro_cano",
            tipo_declaracion="Acusacion",
            evento_descrito=evento,
            cita_textual_evidencia="             ",
            folio=1,
            expediente_id="exp_ccc_14_18"
        )


def test_regla_declarante_obligatorio():
    """Una afirmación histórica exige obligatoriamente un declarante."""
    evento = EventoHistorico(
        id="evento_test",
        tipo_evento="Denuncia",
        categoria_tematica="Judicial_Conflictos"
    )

    with pytest.raises(ValidationError):
        AfirmacionHistorica(
            id="afirmacion_sin_declarante",
            declarante_id="   ",  # Declarante vacío
            tipo_declaracion="Acusacion",
            evento_descrito=evento,
            cita_textual_evidencia="declaró que habían ocultado a los tributarios",
            folio=1,
            expediente_id="exp_ccc_14_18"
        )
