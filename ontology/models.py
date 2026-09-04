"""
Modelos de Dominio Pydantic v2 - Ontología Histórica del Archivo del Cusco (OHAC)

Implementa la arquitectura 'Code-First Ontology' combinando:
- RiC-O (Organización archivística)
- CIDOC CRM (Eventos, actores, lugares, objetos)
- PROV-O (Procedencia inquebrantable de afirmaciones y evidencias)
- SKOS (Nombres canónicos y variantes ortográficas históricas)
- OHAC (Extensiones para el mundo andino colonial y reificación de testimonios/afirmaciones)
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


# =====================================================================
# 1. PROCEDENCIA ARCHIVÍSTICA (Inspirado en RiC-O: RecordSet, RecordPart)
# =====================================================================

class UnidadArchivistica(BaseModel):
    """
    Equivalente a rico:RecordSet y rico:RecordPart.
    Garantiza la localización física y procedencia de cualquier dato.
    """
    fondo: str = Field(default="Intendencia", description="Fondo documental del Archivo Regional del Cusco")
    serie: str = Field(default="Causas Criminales", description="Serie documental (ej. Causas Criminales, Causas Ordinarias)")
    legajo: int = Field(..., description="Número de legajo físico")
    expediente: int = Field(..., description="Número de expediente")
    folio: int = Field(..., description="Número de folio del cual se extrae la información")
    fragmento_id: str = Field(..., description="Identificador único del fragmento o párrafo (ej. exp18_f01_frag01)")
    texto_original: Optional[str] = Field(None, description="Texto transcrito literal original")
    texto_modernizado: Optional[str] = Field(None, description="Texto normalizado/modernizado para procesamiento")

    model_config = ConfigDict(extra="forbid")


# =====================================================================
# 2. ESPACIO Y RECURSOS MATERIALES (Inspirado en CIDOC CRM: E53_Place, E70_Thing)
# =====================================================================

class Lugar(BaseModel):
    """
    Equivalente a crm:E53_Place.
    Localidades, doctrinas, ayllus territoriales y edificios institucionales.
    """
    id: str = Field(..., description="Identificador normalizado (ej. lugar_tinta, lugar_carcel_tinta)")
    nombre_mencionado: str = Field(..., description="Nombre tal como aparece en el texto")
    tipo_lugar: Literal[
        "Pueblo", "Ciudad", "Ayllu_Territorio", "Hacienda",
        "Edificio_Institucion", "Parroquia_Doctrina", "Partido_Provincia", "Otro"
    ]
    jurisdiccion_superior: Optional[str] = Field(None, description="Jurisdicción de mayor jerarquía (ej. Partido de Tinta, Intendencia del Cusco)")


class ObjetoOBien(BaseModel):
    """
    Equivalente a crm:E70_Thing.
    Bienes, tributos, sumas de dinero o derechos en disputa.
    """
    id: str = Field(..., description="Identificador del bien")
    descripcion: str = Field(..., description="Descripción (ej. '51 indios tributarios', 'Hacienda Huasacona', '500 pesos en plata')")
    tipo_bien: Literal[
        "Indios_Tributarios", "Dinero_Tributo", "Inmueble_Tierra",
        "Mueble_Mercancia", "Cargo_Titulo", "Arma_Herramienta", "Otro"
    ]
    cantidad_o_valor: Optional[str] = Field(None, description="Monto o cantidad explícita")


# =====================================================================
# 3. ACTORES HISTÓRICOS Y VARIANTES (CIDOC CRM E21/E74 + SKOS + OHAC Ayllu)
# =====================================================================

class ActorHistorico(BaseModel):
    """
    Equivalente a crm:E21_Person o crm:E74_Group + skos:prefLabel / skos:altLabel.
    Integra la extensión OHAC para 'Ayllu_Comunidad' y 'CondicionTributaria'.
    """
    id_canonico: str = Field(..., description="URI o ID único canónico (ej. persona_manuel_huancachoque)")
    nombre_principal: str = Field(..., description="skos:prefLabel: Forma canónica normalizada")
    variantes_ortograficas: List[str] = Field(
        default_factory=list,
        description="skos:altLabel: Grafías históricas variantes encontradas (ej. 'Guancachoque', 'Mancachoque')"
    )
    tipo_actor: Literal[
        "Persona", "Ayllu_Comunidad", "Institucion_Gobierno",
        "Institucion_Eclesiastica", "Familia_Colectivo", "Cuerpo_Militar"
    ]
    condicion_socioetnica: Optional[Literal[
        "IndioOriginario", "IndioForastero", "IndioTributario", "Reservado",
        "EspanolVecino", "Mestizo", "Noble_Cacique", "Eclesiástico", "Desconocido"
    ]] = Field(None, description="Condición fiscal o sociorracial colonial explícitamente atribuida")
    cargos_mencionados: List[str] = Field(
        default_factory=list,
        description="Cargos o rangos referidos en el texto (ej. 'Sargento de Milicias', 'Cacique Recaudador', 'Subdelegado')"
    )


# =====================================================================
# 4. EVENTOS Y PARTICIPACIÓN (CIDOC CRM: E5_Event + P11_had_participant)
# =====================================================================

class Participacion(BaseModel):
    """
    Relación de participación tipada (N-ary relation).
    """
    actor_id: str = Field(..., description="ID del actor participante")
    rol: str = Field(..., description="Rol específico (ej. 'Denunciante', 'Denunciado', 'Victima', 'Testigo', 'Agresor_Alegado', 'Juez_Subdelegado', 'Escribano')")
    calidad_participacion: Optional[str] = Field(None, description="Detalle contextual (ej. 'Bajo juramento de cruz', 'Por coacción', 'Ausente')")


class EventoHistorico(BaseModel):
    """
    Equivalente a crm:E5_Event / crm:E7_Activity.
    El suceso espaciotemporal sobre el que versa el documento o testimonio.
    """
    id: str = Field(..., description="Identificador único del evento")
    tipo_evento: str = Field(..., description="Clase de evento (ej. 'Denuncia', 'Ocultacion_Tributarios', 'Agresion_Fisica', 'Encarcelamiento', 'Tumulto_Alboroto', 'Revisita', 'ResolucionJudicial', 'Compraventa', 'Testamento')")
    categoria_tematica: Literal[
        "Judicial_Conflictos", "Fiscal_Tributario", "Tierras_Propiedad",
        "Eclesiastico_Religioso", "Administrativo_Politico", "Familiar_Personal"
    ]
    fecha_mencionada: Optional[str] = Field(None, description="crm:P4_has_time-span: Fecha textual o año referenciado")
    lugar: Optional[str] = Field(None, description="crm:P7_took_place_at: ID o nombre del lugar")
    participantes: List[Participacion] = Field(default_factory=list, description="crm:P11_had_participant: Actores con sus respectivos roles")
    objetos_involucrados: List[ObjetoOBien] = Field(default_factory=list, description="Objetos o bienes afectados")


# =====================================================================
# 5. REIFICACIÓN EPISTÉMICA: AFIRMACIONES Y PROCEDENCIA (OHAC + PROV-O)
# =====================================================================

class AfirmacionHistorica(BaseModel):
    """
    Clase central de OHAC (Extension de PROV-O).
    Evita transformar acusaciones subjetivas o falsedades en hechos históricos demostrados.
    """
    id: str = Field(..., description="Identificador único de la afirmación")
    declarante_id: str = Field(..., description="prov:wasAttributedTo: ID del actor que formula la declaración")
    tipo_declaracion: Literal[
        "TestimonioDirecto", "Acusacion", "Sospecha",
        "ResolucionOficial", "Confesion_Rectificacion"
    ] = Field(..., description="Modalidad enunciativa del testimonio")
    estado_epistemologico: Literal[
        "Alegato_No_Comprobado", "Confirmado_Oficial", "Desmentido_Falso", "En_Disputa"
    ] = Field(default="Alegato_No_Comprobado", description="Estatus epistemológico dentro del proceso")
    evento_descrito: EventoHistorico = Field(..., description="El evento tal como fue narrado por el declarante")
    cita_textual_evidencia: str = Field(
        ...,
        min_length=10,
        description="prov:wasDerivedFrom: Cita literal obligatoria que respalda la afirmación."
    )
    folio: int = Field(..., description="Número de folio físico donde se halla la cita")
    expediente_id: str = Field(..., description="Identificador del expediente fuente")
    
    # Relaciones epistémicas entre testimonios
    contradice_afirmacion_ids: List[str] = Field(
        default_factory=list,
        description="ohac:contradice: IDs de afirmaciones que entran en contradicción directa con esta"
    )
    ratifica_afirmacion_ids: List[str] = Field(
        default_factory=list,
        description="ohac:ratifica: IDs de testimonios que apoyan o confirman esta afirmación"
    )
    confianza_extraccion: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Puntuación de fiabilidad del extractor (LLM o regla)"
    )

    @field_validator("cita_textual_evidencia")
    @classmethod
    def validar_cita_no_vacia(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Regla Ontológica OHAC violada: Toda afirmación histórica exige una cita textual obligatoria.")
        return v.strip()

    @field_validator("declarante_id")
    @classmethod
    def validar_declarante(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Regla Ontológica OHAC violada: Toda afirmación debe tener un declarante identificado.")
        return v.strip()


# =====================================================================
# 6. ENVOLTORIO DE EXTRACCIÓN DOCUMENTAL (Batch de Folio / Documento)
# =====================================================================

class ExtraccionFolio(BaseModel):
    """
    Contrato de datos de salida que el LLM está obligado a producir
    por cada folio o acto procesal analizado.
    """
    unidad_archivistica: UnidadArchivistica
    actores: List[ActorHistorico] = Field(default_factory=list)
    lugares: List[Lugar] = Field(default_factory=list)
    objetos: List[ObjetoOBien] = Field(default_factory=list)
    afirmaciones: List[AfirmacionHistorica] = Field(default_factory=list)
    eventos_institucionales_probados: List[EventoHistorico] = Field(
        default_factory=list,
        description="Eventos procesales objetivos y verificables (ej. 'Emisión de auto judicial', 'Presentación formal de escrito')"
    )
