"""
Motor de Cálculo de Estadísticas y Calidad del Grafo de Conocimiento (KGCQ)
===========================================================================
Implementa la batería de métricas de calidad inspirada en:
"Ontology-grounded Automatic Knowledge Graph Construction by LLM" (Feng et al., KDD 2024).

Dimensiones analizadas:
  1. Conformidad con el Esquema Ontológico (Schema Conformance & Domain/Range)
  2. Fidelidad de Anclaje Textual (Grounding & Evidence Veracity)
  3. Canonicalización y Normalización de Entidades (SKOS prefLabel / altLabel)
  4. Balance Epistémico y Crítica de Fuentes (OHAC / PROV-O)
  5. Topología, Centralidad y Conectividad del Grafo
  6. Índice Compuesto de Calidad de Construcción (KGCQ Index)
"""

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rapidfuzz import fuzz

# Metamodelo de relaciones permitidas entre etiquetas
# (origen_etiqueta, tipo_arista) -> conjunto de etiquetas destino válidas
METAMODELO_DOMINIO_RANGO = {
    ("Actor", "MENCIONADO_EN"): {"FuenteArchivistica"},
    ("Lugar", "MENCIONADO_EN"): {"FuenteArchivistica"},
    ("ObjetoBien", "MENCIONADO_EN"): {"FuenteArchivistica"},
    ("EventoInstitucional", "DOCUMENTADO_EN"): {"FuenteArchivistica"},
    ("AfirmacionHistorica", "EXTRAIDO_DE"): {"FuenteArchivistica"},
    ("Actor", "DECLARO"): {"AfirmacionHistorica"},
    ("AfirmacionHistorica", "DESCRIBE_EVENTO"): {"EventoTestimoniado"},
    ("Actor", "ROL_EN_EVENTO"): {"EventoTestimoniado"},
    ("Actor", "PARTICIPA_EN"): {"EventoInstitucional"},
    ("EventoInstitucional", "OCURRE_EN"): {"Lugar"},
    ("EventoTestimoniado", "OCURRE_EN"): {"Lugar"},
    ("EventoInstitucional", "INVOLUCRA_BIEN"): {"ObjetoBien"},
    ("EventoTestimoniado", "INVOLUCRA_BIEN"): {"ObjetoBien"},
    ("AfirmacionHistorica", "CONTRADICE"): {"AfirmacionHistorica"},
    ("AfirmacionHistorica", "RATIFICA"): {"AfirmacionHistorica"},
}


@dataclass
class MetricasEsquema:
    total_nodos: int
    nodos_por_etiqueta: Dict[str, int]
    total_aristas: int
    aristas_por_tipo: Dict[str, int]
    aristas_validas_metamodelo: int
    aristas_invalidas_metamodelo: int
    aristas_rotas_referenciales: int
    nodos_aislados: int
    tasa_conformidad_metamodelo: float
    tasa_integridad_referencial: float


@dataclass
class MetricasAnclaje:
    total_citas_evaluadas: int
    citas_coincidencia_exacta: int
    tasa_coincidencia_exacta: float
    citas_anclaje_alto: int      # rapidfuzz partial_ratio >= 85%
    tasa_anclaje_alto: float
    citas_anclaje_medio: int     # 70% <= partial_ratio < 85%
    tasa_anclaje_medio: float
    citas_riesgo_alucinacion: int # partial_ratio < 70%
    tasa_riesgo_alucinacion: float
    longitud_promedio_chars: float
    longitud_min_chars: int
    longitud_max_chars: int
    confianza_promedio_extractor: float
    score_fidelidad_anclaje: float


@dataclass
class MetricasCanonicalizacion:
    total_actores_canonicos: int
    actores_con_variantes: int
    total_variantes_ortograficas: int
    promedio_variantes_por_actor: float
    ratio_consolidadas_vs_superficie: float
    actores_con_condicion_socioetnica: int
    tasa_condicion_socioetnica: float
    actores_con_cargos_registrados: int
    tasa_cargos_registrados: float
    score_canonicalizacion: float


@dataclass
class MetricasEpistemicas:
    total_afirmaciones: int
    distribucion_estados: Dict[str, int]
    distribucion_tipos_declaracion: Dict[str, int]
    total_relaciones_contradiccion: int
    total_relaciones_ratificacion: int
    afirmaciones_en_disputa_o_litigio: int
    tasa_reificacion_epistemica: float


@dataclass
class ActorCentralidad:
    id: str
    nombre: str
    tipo: str
    condicion: Optional[str]
    grado: int
    grado_entrada: int
    grado_salida: int


@dataclass
class MetricasTopologia:
    densidad_grafo: float
    grado_promedio: float
    total_componentes_conexas: int
    tamano_componente_gigante: int
    cobertura_componente_gigante: float
    top_actores_centralidad: List[ActorCentralidad]


@dataclass
class IndiceCalidadKGCQ:
    score_global: float
    calificacion_letra: str
    diagnostico: str
    subscores: Dict[str, float]


@dataclass
class EstadisticasCalidad:
    esquema: MetricasEsquema
    anclaje: MetricasAnclaje
    canonicalizacion: MetricasCanonicalizacion
    epistemica: MetricasEpistemicas
    topologia: MetricasTopologia
    calidad_kgcq: IndiceCalidadKGCQ

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvaluadorCalidadGrafo:
    """Evalúa la calidad del grafo construido a partir de los datos y el corpus fuente."""

    def __init__(
        self,
        ruta_grafo_json: Path,
        ruta_extracciones_jsonl: Path,
        ruta_corpus_txt: Path,
    ):
        self.ruta_grafo_json = Path(ruta_grafo_json)
        self.ruta_extracciones_jsonl = Path(ruta_extracciones_jsonl)
        self.ruta_corpus_txt = Path(ruta_corpus_txt)

        self._cargar_datos()

    def _cargar_datos(self) -> None:
        if not self.ruta_grafo_json.exists():
            raise FileNotFoundError(f"No existe {self.ruta_grafo_json}")
        with self.ruta_grafo_json.open(encoding="utf-8") as f:
            self.grafo = json.load(f)

        self.nodos = {n["id"]: n for n in self.grafo.get("nodos", [])}
        self.aristas = self.grafo.get("aristas", [])

        self.extracciones: List[Dict[str, Any]] = []
        if self.ruta_extracciones_jsonl.exists():
            with self.ruta_extracciones_jsonl.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.extracciones.append(json.loads(line))

        self.texto_corpus = ""
        if self.ruta_corpus_txt.exists():
            self.texto_corpus = self.ruta_corpus_txt.read_text(encoding="utf-8", errors="replace")

    def evaluar_esquema(self) -> MetricasEsquema:
        conteo_nodos = Counter(n.get("etiqueta", "Desconocido") for n in self.nodos.values())
        conteo_aristas = Counter(a.get("tipo", "Desconocido") for a in self.aristas)

        rotas = 0
        validas_meta = 0
        invalidas_meta = 0

        grados = defaultdict(int)

        for a in self.aristas:
            u, v, tipo = a.get("origen"), a.get("destino"), a.get("tipo")
            if u not in self.nodos or v not in self.nodos:
                rotas += 1
                continue

            grados[u] += 1
            grados[v] += 1

            etiq_u = self.nodos[u].get("etiqueta")
            etiq_v = self.nodos[v].get("etiqueta")

            destinos_permitidos = METAMODELO_DOMINIO_RANGO.get((etiq_u, tipo))
            if destinos_permitidos and etiq_v in destinos_permitidos:
                validas_meta += 1
            else:
                invalidas_meta += 1

        total_aristas = len(self.aristas)
        nodos_aislados = sum(1 for nid in self.nodos if grados[nid] == 0)

        tasa_integridad = 1.0 - (rotas / total_aristas) if total_aristas > 0 else 1.0
        aristas_no_rotas = total_aristas - rotas
        tasa_conformidad = (validas_meta / aristas_no_rotas) if aristas_no_rotas > 0 else 1.0

        return MetricasEsquema(
            total_nodos=len(self.nodos),
            nodos_por_etiqueta=dict(conteo_nodos),
            total_aristas=total_aristas,
            aristas_por_tipo=dict(conteo_aristas),
            aristas_validas_metamodelo=validas_meta,
            aristas_invalidas_metamodelo=invalidas_meta,
            aristas_rotas_referenciales=rotas,
            nodos_aislados=nodos_aislados,
            tasa_conformidad_metamodelo=round(tasa_conformidad, 4),
            tasa_integridad_referencial=round(tasa_integridad, 4),
        )

    def evaluar_anclaje(self) -> MetricasAnclaje:
        citas: List[Tuple[str, float]] = []
        for ext in self.extracciones:
            for af in ext.get("afirmaciones", []):
                cita = af.get("cita_textual_evidencia", "").strip()
                conf = float(af.get("confianza_extraccion", 1.0))
                if cita:
                    citas.append((cita, conf))

        if not citas:
            return MetricasAnclaje(
                total_citas_evaluadas=0,
                citas_coincidencia_exacta=0,
                tasa_coincidencia_exacta=0.0,
                citas_anclaje_alto=0,
                tasa_anclaje_alto=0.0,
                citas_anclaje_medio=0,
                tasa_anclaje_medio=0.0,
                citas_riesgo_alucinacion=0,
                tasa_riesgo_alucinacion=0.0,
                longitud_promedio_chars=0.0,
                longitud_min_chars=0,
                longitud_max_chars=0,
                confianza_promedio_extractor=0.0,
                score_fidelidad_anclaje=0.0,
            )

        corpus_lower = self.texto_corpus.lower()
        exactas = 0
        alto = 0
        medio = 0
        riesgo = 0
        longitudes = []
        confianzas = []

        for cita, conf in citas:
            longitudes.append(len(cita))
            confianzas.append(conf)

            if cita in self.texto_corpus:
                exactas += 1
                alto += 1
            else:
                # Búsqueda difusa de subsecuencia en texto histórico
                sim = fuzz.partial_ratio(cita.lower(), corpus_lower)
                if sim >= 85:
                    alto += 1
                elif sim >= 70:
                    medio += 1
                else:
                    riesgo += 1

        total = len(citas)
        tasa_exacta = exactas / total
        tasa_alto = alto / total
        tasa_medio = medio / total
        tasa_riesgo = riesgo / total
        conf_prom = sum(confianzas) / total

        # Score ponderado: 1.0 para alto, 0.5 para medio, 0 para riesgo
        score_anclaje = (alto * 1.0 + medio * 0.5) / total

        return MetricasAnclaje(
            total_citas_evaluadas=total,
            citas_coincidencia_exacta=exactas,
            tasa_coincidencia_exacta=round(tasa_exacta, 4),
            citas_anclaje_alto=alto,
            tasa_anclaje_alto=round(tasa_alto, 4),
            citas_anclaje_medio=medio,
            tasa_anclaje_medio=round(tasa_medio, 4),
            citas_riesgo_alucinacion=riesgo,
            tasa_riesgo_alucinacion=round(tasa_riesgo, 4),
            longitud_promedio_chars=round(sum(longitudes) / total, 1),
            longitud_min_chars=min(longitudes),
            longitud_max_chars=max(longitudes),
            confianza_promedio_extractor=round(conf_prom, 3),
            score_fidelidad_anclaje=round(score_anclaje, 4),
        )

    def evaluar_canonicalizacion(self) -> MetricasCanonicalizacion:
        actores = [n for n in self.nodos.values() if n.get("etiqueta") == "Actor"]
        total_actores = len(actores)
        if total_actores == 0:
            return MetricasCanonicalizacion(
                total_actores_canonicos=0,
                actores_con_variantes=0,
                total_variantes_ortograficas=0,
                promedio_variantes_por_actor=0.0,
                ratio_consolidadas_vs_superficie=0.0,
                actores_con_condicion_socioetnica=0,
                tasa_condicion_socioetnica=0.0,
                actores_con_cargos_registrados=0,
                tasa_cargos_registrados=0.0,
                score_canonicalizacion=0.0,
            )

        con_variantes = 0
        total_variantes = 0
        con_condicion = 0
        con_cargos = 0

        for a in actores:
            vars_ = a.get("variantes", [])
            if vars_:
                con_variantes += 1
                total_variantes += len(vars_)

            cond = a.get("condicion")
            if cond and cond != "Desconocido":
                con_condicion += 1

            cargos = a.get("cargos", [])
            if cargos:
                con_cargos += 1

        prom_variantes = total_variantes / total_actores
        # Total de formas superficiales históricas unificadas bajo este universo canónico
        formas_superficie = total_actores + total_variantes
        ratio_consol = formas_superficie / total_actores

        tasa_condicion = con_condicion / total_actores
        tasa_cargos = con_cargos / total_actores

        score_can = (tasa_condicion * 0.4 + tasa_cargos * 0.3 + min(prom_variantes, 2.0) / 2.0 * 0.3)

        return MetricasCanonicalizacion(
            total_actores_canonicos=total_actores,
            actores_con_variantes=con_variantes,
            total_variantes_ortograficas=total_variantes,
            promedio_variantes_por_actor=round(prom_variantes, 2),
            ratio_consolidadas_vs_superficie=round(ratio_consol, 2),
            actores_con_condicion_socioetnica=con_condicion,
            tasa_condicion_socioetnica=round(tasa_condicion, 4),
            actores_con_cargos_registrados=con_cargos,
            tasa_cargos_registrados=round(tasa_cargos, 4),
            score_canonicalizacion=round(score_can, 4),
        )

    def evaluar_epistemica(self) -> MetricasEpistemicas:
        afirmaciones = [n for n in self.nodos.values() if n.get("etiqueta") == "AfirmacionHistorica"]
        total_af = len(afirmaciones)

        estados = Counter(n.get("estado", "Desconocido") for n in afirmaciones)
        tipos_dec = Counter(n.get("tipo", "Desconocido") for n in afirmaciones)

        contradicciones = sum(1 for a in self.aristas if a.get("tipo") == "CONTRADICE")
        ratificaciones = sum(1 for a in self.aristas if a.get("tipo") == "RATIFICA")

        en_disputa = estados.get("En_Disputa", 0) + estados.get("Alegato_No_Comprobado", 0)

        # Tasa de reificación epistémica: todas las afirmaciones cuentan con cita obligatoria
        reificadas = sum(1 for a in afirmaciones if a.get("cita"))
        tasa_reificacion = (reificadas / total_af) if total_af > 0 else 1.0

        return MetricasEpistemicas(
            total_afirmaciones=total_af,
            distribucion_estados=dict(estados),
            distribucion_tipos_declaracion=dict(tipos_dec),
            total_relaciones_contradiccion=contradicciones,
            total_relaciones_ratificacion=ratificaciones,
            afirmaciones_en_disputa_o_litigio=en_disputa,
            tasa_reificacion_epistemica=round(tasa_reificacion, 4),
        )

    def evaluar_topologia(self) -> MetricasTopologia:
        v_count = len(self.nodos)
        e_count = len(self.aristas)

        if v_count < 2:
            return MetricasTopologia(
                densidad_grafo=0.0,
                grado_promedio=0.0,
                total_componentes_conexas=0,
                tamano_componente_gigante=0,
                cobertura_componente_gigante=0.0,
                top_actores_centralidad=[],
            )

        densidad = (2.0 * e_count) / (v_count * (v_count - 1))
        grado_prom = (2.0 * e_count) / v_count

        # Grafo no dirigido para componentes conexas y grados
        adj: Dict[str, Set[str]] = defaultdict(set)
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)

        for a in self.aristas:
            u, v = a.get("origen"), a.get("destino")
            if u in self.nodos and v in self.nodos:
                adj[u].add(v)
                adj[v].add(u)
                out_degree[u] += 1
                in_degree[v] += 1

        # Componentes conexas vía BFS
        visitados = set()
        componentes = []
        for n in self.nodos:
            if n not in visitados:
                comp = []
                queue = deque([n])
                visitados.add(n)
                while queue:
                    curr = queue.popleft()
                    comp.append(curr)
                    for vecino in adj[curr]:
                        if vecino not in visitados:
                            visitados.add(vecino)
                            queue.append(vecino)
                componentes.append(comp)

        tamano_gigante = max(len(c) for c in componentes) if componentes else 0
        cobertura_gigante = tamano_gigante / v_count if v_count > 0 else 0.0

        # Centralidad de actores
        actores = [n for n in self.nodos.values() if n.get("etiqueta") == "Actor"]
        centralidades: List[ActorCentralidad] = []

        for a in actores:
            nid = a["id"]
            d_total = len(adj[nid])
            d_in = in_degree[nid]
            d_out = out_degree[nid]
            centralidades.append(
                ActorCentralidad(
                    id=nid,
                    nombre=a.get("nombre", nid),
                    tipo=a.get("tipo", "Persona"),
                    condicion=a.get("condicion"),
                    grado=d_total,
                    grado_entrada=d_in,
                    grado_salida=d_out,
                )
            )

        centralidades.sort(key=lambda x: x.grado, reverse=True)
        top_actores = centralidades[:10]

        return MetricasTopologia(
            densidad_grafo=round(densidad, 5),
            grado_promedio=round(grado_prom, 2),
            total_componentes_conexas=len(componentes),
            tamano_componente_gigante=tamano_gigante,
            cobertura_componente_gigante=round(cobertura_gigante, 4),
            top_actores_centralidad=top_actores,
        )

    def calcular_indice_calidad(
        self,
        esquema: MetricasEsquema,
        anclaje: MetricasAnclaje,
        canonicalizacion: MetricasCanonicalizacion,
        epistemica: MetricasEpistemicas,
        topologia: MetricasTopologia,
    ) -> IndiceCalidadKGCQ:
        """
        Calcula el Índice Compuesto KGCQ (Knowledge Graph Construction Quality Index)
        ponderando las 5 dimensiones clave.
        """
        # 1. Conformidad con el metamodelo (25%)
        s_conformidad = (
            esquema.tasa_conformidad_metamodelo * 0.6
            + esquema.tasa_integridad_referencial * 0.4
        ) * 100.0

        # 2. Fidelidad de anclaje textual (30%)
        s_anclaje = anclaje.score_fidelidad_anclaje * 100.0

        # 3. Integridad y conectividad estructural (20%)
        s_integridad = (
            topologia.cobertura_componente_gigante * 0.7
            + (1.0 - (esquema.nodos_aislados / esquema.total_nodos if esquema.total_nodos else 0.0)) * 0.3
        ) * 100.0

        # 4. Canonicalización y normalización de entidades (15%)
        s_canonicalizacion = canonicalizacion.score_canonicalizacion * 100.0

        # 5. Reificación y completitud epistémica (10%)
        s_epistemico = epistemica.tasa_reificacion_epistemica * 100.0

        score_global = (
            s_conformidad * 0.25
            + s_anclaje * 0.30
            + s_integridad * 0.20
            + s_canonicalizacion * 0.15
            + s_epistemico * 0.10
        )

        subscores = {
            "conformidad_metamodelo": round(s_conformidad, 2),
            "fidelidad_anclaje_textual": round(s_anclaje, 2),
            "conectividad_estructural": round(s_integridad, 2),
            "canonicalizacion_skos": round(s_canonicalizacion, 2),
            "completitud_epistemica": round(s_epistemico, 2),
        }

        if score_global >= 90.0:
            letra = "A+"
            diag = "Construcción sobresaliente: rigurosamente anclada al corpus y conformante al metamodelo ontológico."
        elif score_global >= 80.0:
            letra = "A"
            diag = "Construcción sólida y de alta fidelidad, lista para análisis y consultas históricas."
        elif score_global >= 70.0:
            letra = "B"
            diag = "Construcción aceptable, con áreas de mejora en anclaje textual o resolución de entidades."
        else:
            letra = "C"
            diag = "Requiere refinamiento en normalización ontológica o control de alucinaciones."

        return IndiceCalidadKGCQ(
            score_global=round(score_global, 2),
            calificacion_letra=letra,
            diagnostico=diag,
            subscores=subscores,
        )

    def ejecutar(self) -> EstadisticasCalidad:
        m_esquema = self.evaluar_esquema()
        m_anclaje = self.evaluar_anclaje()
        m_canon = self.evaluar_canonicalizacion()
        m_epist = self.evaluar_epistemica()
        m_topo = self.evaluar_topologia()

        kgcq = self.calcular_indice_calidad(
            esquema=m_esquema,
            anclaje=m_anclaje,
            canonicalizacion=m_canon,
            epistemica=m_epist,
            topologia=m_topo,
        )

        return EstadisticasCalidad(
            esquema=m_esquema,
            anclaje=m_anclaje,
            canonicalizacion=m_canon,
            epistemica=m_epist,
            topologia=m_topo,
            calidad_kgcq=kgcq,
        )


def calcular_estadisticas_completas(
    ruta_grafo: Path,
    ruta_extracciones: Path,
    ruta_corpus: Path,
) -> EstadisticasCalidad:
    evaluador = EvaluadorCalidadGrafo(
        ruta_grafo_json=ruta_grafo,
        ruta_extracciones_jsonl=ruta_extracciones,
        ruta_corpus_txt=ruta_corpus,
    )
    return evaluador.ejecutar()
