"""
Constructor del Grafo de Conocimiento Histórico
================================================
Convierte las ExtraccionFolio validadas por Pydantic en un grafo Neo4j.

Esquema de nodos (etiquetas):
  :FuenteArchivistica   — Folio o fragmento de documento físico
  :Actor                — Persona, ayllu, institución histórica
  :Lugar                — Pueblo, ciudad, edificio, parroquia
  :ObjetoBien           — Bien material, tributo, dinero
  :EventoInstitucional  — Hecho procesal verificado (auto, decreto, matriculación)
  :EventoTestimoniado   — Evento narrado en un testimonio (puede ser falso)
  :AfirmacionHistorica  — Reificación epistémica de testimonios

Tipos de aristas:
  (Actor)-[:MENCIONADO_EN]->(FuenteArchivistica)
  (Actor)-[:DECLARO]->(AfirmacionHistorica)
  (AfirmacionHistorica)-[:DESCRIBE_EVENTO]->(EventoTestimoniado)
  (AfirmacionHistorica)-[:EXTRAIDO_DE]->(FuenteArchivistica)
  (AfirmacionHistorica)-[:CONTRADICE]->(AfirmacionHistorica)
  (AfirmacionHistorica)-[:RATIFICA]->(AfirmacionHistorica)
  (Actor)-[:ROL_EN_EVENTO {rol}]->(EventoTestimoniado)
  (Actor)-[:PARTICIPA_EN {rol}]->(EventoInstitucional)
  (EventoInstitucional)-[:OCURRE_EN]->(Lugar)
  (EventoTestimoniado)-[:ALEGADO_EN]->(Lugar)
  (Actor)-[:MIEMBRO_DE]->(Lugar)   # p.e. Actor del Ayllu Tinta
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from ontology.models import ExtraccionFolio


# =====================================================================
# SETUP DE CONSTRAINTS E INDICES EN NEO4J
# =====================================================================

SETUP_CYPHER = """
CREATE CONSTRAINT actor_id IF NOT EXISTS
  FOR (n:Actor) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT fuente_id IF NOT EXISTS
  FOR (n:FuenteArchivistica) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT lugar_id IF NOT EXISTS
  FOR (n:Lugar) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT objeto_id IF NOT EXISTS
  FOR (n:ObjetoBien) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT evento_inst_id IF NOT EXISTS
  FOR (n:EventoInstitucional) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT evento_test_id IF NOT EXISTS
  FOR (n:EventoTestimoniado) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT afirmacion_id IF NOT EXISTS
  FOR (n:AfirmacionHistorica) REQUIRE n.id IS UNIQUE;

CREATE INDEX actor_nombre IF NOT EXISTS
  FOR (n:Actor) ON (n.nombre);

CREATE INDEX afirmacion_estado IF NOT EXISTS
  FOR (n:AfirmacionHistorica) ON (n.estado);
"""


# =====================================================================
# FUNCIONES DE MERGE (UPSERT) EN NEO4J
# =====================================================================

def _merge_fuente(tx, ua):
    tx.run("""
        MERGE (f:FuenteArchivistica {id: $id})
        SET f.fondo       = $fondo,
            f.serie       = $serie,
            f.legajo      = $legajo,
            f.expediente  = $expediente,
            f.folio       = $folio
    """,
        id=ua.fragmento_id,
        fondo=ua.fondo,
        serie=ua.serie,
        legajo=ua.legajo,
        expediente=ua.expediente,
        folio=ua.folio,
    )


def _merge_actor(tx, actor, fuente_id: str):
    tx.run("""
        MERGE (a:Actor {id: $id})
        SET a.nombre     = $nombre,
            a.variantes  = $variantes,
            a.tipo       = $tipo,
            a.condicion  = $condicion,
            a.cargos     = $cargos
        WITH a
        MATCH (f:FuenteArchivistica {id: $fuente_id})
        MERGE (a)-[:MENCIONADO_EN]->(f)
    """,
        id=actor.id_canonico,
        nombre=actor.nombre_principal,
        variantes=actor.variantes_ortograficas,
        tipo=actor.tipo_actor,
        condicion=actor.condicion_socioetnica,
        cargos=actor.cargos_mencionados,
        fuente_id=fuente_id,
    )


def _merge_lugar(tx, lugar, fuente_id: str):
    tx.run("""
        MERGE (l:Lugar {id: $id})
        SET l.nombre        = $nombre,
            l.tipo          = $tipo,
            l.jurisdiccion  = $jurisdiccion
        WITH l
        MATCH (f:FuenteArchivistica {id: $fuente_id})
        MERGE (l)-[:MENCIONADO_EN]->(f)
    """,
        id=lugar.id,
        nombre=lugar.nombre_mencionado,
        tipo=lugar.tipo_lugar,
        jurisdiccion=lugar.jurisdiccion_superior,
        fuente_id=fuente_id,
    )


def _merge_objeto(tx, obj, fuente_id: str):
    tx.run("""
        MERGE (o:ObjetoBien {id: $id})
        SET o.descripcion = $descripcion,
            o.tipo        = $tipo,
            o.cantidad    = $cantidad
        WITH o
        MATCH (f:FuenteArchivistica {id: $fuente_id})
        MERGE (o)-[:MENCIONADO_EN]->(f)
    """,
        id=f"objeto_{obj.id}",
        descripcion=obj.descripcion,
        tipo=obj.tipo_bien,
        cantidad=obj.cantidad_o_valor,
        fuente_id=fuente_id,
    )


def _merge_evento_institucional(tx, evento, fuente_id: str):
    tx.run("""
        MERGE (e:EventoInstitucional {id: $id})
        SET e.tipo_evento  = $tipo_evento,
            e.categoria    = $categoria,
            e.fecha        = $fecha,
            e.lugar_id     = $lugar_id
        WITH e
        MATCH (f:FuenteArchivistica {id: $fuente_id})
        MERGE (e)-[:DOCUMENTADO_EN]->(f)
    """,
        id=evento.id,
        tipo_evento=evento.tipo_evento,
        categoria=evento.categoria_tematica,
        fecha=evento.fecha_mencionada,
        lugar_id=evento.lugar,
        fuente_id=fuente_id,
    )

    # Participantes en el evento institucional
    for p in evento.participantes:
        tx.run("""
            MATCH (a:Actor {id: $actor_id})
            MATCH (e:EventoInstitucional {id: $evento_id})
            MERGE (a)-[r:PARTICIPA_EN]->(e)
            SET r.rol = $rol,
                r.calidad = $calidad
        """,
            actor_id=p.actor_id,
            evento_id=evento.id,
            rol=p.rol,
            calidad=p.calidad_participacion,
        )

    # Lugar del evento institucional
    if evento.lugar:
        tx.run("""
            MATCH (e:EventoInstitucional {id: $evento_id})
            MATCH (l:Lugar)
            WHERE l.id = $lugar_id OR toLower(l.nombre) = toLower($lugar_id) OR toLower(l.id) CONTAINS toLower($lugar_id)
            MERGE (e)-[:OCURRE_EN]->(l)
        """, evento_id=evento.id, lugar_id=evento.lugar)

    # Objetos y bienes involucrados en el evento institucional
    for obj in evento.objetos_involucrados:
        tx.run("""
            MATCH (e:EventoInstitucional {id: $evento_id})
            MATCH (o:ObjetoBien {id: $objeto_id})
            MERGE (e)-[:INVOLUCRA_BIEN]->(o)
        """, evento_id=evento.id, objeto_id=f"objeto_{obj.id}")


def _merge_afirmacion(tx, afirm, fuente_id: str):
    ev = afirm.evento_descrito

    # Nodo del evento tal como fue narrado (puede ser falso)
    tx.run("""
        MERGE (e:EventoTestimoniado {id: $id})
        SET e.tipo_evento   = $tipo_evento,
            e.categoria     = $categoria,
            e.fecha_alegada = $fecha,
            e.lugar_alegado = $lugar
    """,
        id=ev.id,
        tipo_evento=ev.tipo_evento,
        categoria=ev.categoria_tematica,
        fecha=ev.fecha_mencionada,
        lugar=ev.lugar,
    )

    # Participantes en el evento narrado
    for p in ev.participantes:
        tx.run("""
            MATCH (a:Actor {id: $actor_id})
            MATCH (e:EventoTestimoniado {id: $evento_id})
            MERGE (a)-[r:ROL_EN_EVENTO]->(e)
            SET r.rol     = $rol,
                r.calidad = $calidad
        """,
            actor_id=p.actor_id,
            evento_id=ev.id,
            rol=p.rol,
            calidad=p.calidad_participacion,
        )

    # Lugar del evento testimoniado
    if ev.lugar:
        tx.run("""
            MATCH (e:EventoTestimoniado {id: $evento_id})
            MATCH (l:Lugar)
            WHERE l.id = $lugar_id OR toLower(l.nombre) = toLower($lugar_id) OR toLower(l.id) CONTAINS toLower($lugar_id)
            MERGE (e)-[:OCURRE_EN]->(l)
        """, evento_id=ev.id, lugar_id=ev.lugar)

    # Objetos y bienes involucrados en el evento testimoniado
    for obj in ev.objetos_involucrados:
        tx.run("""
            MATCH (e:EventoTestimoniado {id: $evento_id})
            MATCH (o:ObjetoBien {id: $objeto_id})
            MERGE (e)-[:INVOLUCRA_BIEN]->(o)
        """, evento_id=ev.id, objeto_id=f"objeto_{obj.id}")

    # Nodo AfirmacionHistorica (la reificación epistémica)
    tx.run("""
        MERGE (af:AfirmacionHistorica {id: $id})
        SET af.tipo_declaracion = $tipo,
            af.estado           = $estado,
            af.cita             = $cita,
            af.folio            = $folio,
            af.expediente_id    = $expediente_id,
            af.confianza        = $confianza
    """,
        id=afirm.id,
        tipo=afirm.tipo_declaracion,
        estado=afirm.estado_epistemologico,
        cita=afirm.cita_textual_evidencia,
        folio=afirm.folio,
        expediente_id=afirm.expediente_id,
        confianza=afirm.confianza_extraccion,
    )

    # Aristas de la afirmación
    # Declarante → AfirmacionHistorica
    tx.run("""
        MATCH (a:Actor {id: $actor_id})
        MATCH (af:AfirmacionHistorica {id: $af_id})
        MERGE (a)-[:DECLARO]->(af)
    """, actor_id=afirm.declarante_id, af_id=afirm.id)

    # AfirmacionHistorica → EventoTestimoniado
    tx.run("""
        MATCH (af:AfirmacionHistorica {id: $af_id})
        MATCH (e:EventoTestimoniado {id: $ev_id})
        MERGE (af)-[:DESCRIBE_EVENTO]->(e)
    """, af_id=afirm.id, ev_id=ev.id)

    # AfirmacionHistorica → FuenteArchivistica
    tx.run("""
        MATCH (af:AfirmacionHistorica {id: $af_id})
        MATCH (f:FuenteArchivistica {id: $fuente_id})
        MERGE (af)-[:EXTRAIDO_DE]->(f)
    """, af_id=afirm.id, fuente_id=fuente_id)

    # Relaciones epistémicas entre afirmaciones
    for otro_id in afirm.contradice_afirmacion_ids:
        tx.run("""
            MATCH (af1:AfirmacionHistorica {id: $af1_id})
            MATCH (af2:AfirmacionHistorica {id: $af2_id})
            MERGE (af1)-[:CONTRADICE]->(af2)
        """, af1_id=afirm.id, af2_id=otro_id)

    for otro_id in afirm.ratifica_afirmacion_ids:
        tx.run("""
            MATCH (af1:AfirmacionHistorica {id: $af1_id})
            MATCH (af2:AfirmacionHistorica {id: $af2_id})
            MERGE (af1)-[:RATIFICA]->(af2)
        """, af1_id=afirm.id, af2_id=otro_id)


# =====================================================================
# FUNCIÓN PRINCIPAL DE CARGA
# =====================================================================

def cargar_en_neo4j(extracciones: list[ExtraccionFolio]) -> dict:
    """
    Carga todas las extracciones en Neo4j.
    Requiere: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD en variables de entorno.

    Returns:
        dict con contadores de nodos y aristas creados.
    """
    from neo4j import GraphDatabase

    uri      = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user     = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")

    if not password:
        raise EnvironmentError(
            "Variable NEO4J_PASSWORD no definida.\n"
            "Añádela al archivo .env: NEO4J_PASSWORD=tu_password"
        )

    print(f"[graph_builder] Conectando a Neo4j en {uri} ...")
    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Verificar conexión
    driver.verify_connectivity()
    print("[graph_builder] Conexión verificada ✓")

    contadores = {
        "fuentes": 0, "actores": 0, "lugares": 0,
        "objetos": 0, "eventos_inst": 0, "afirmaciones": 0,
    }

    with driver.session() as session:
        # Crear constraints e índices (idempotente)
        print("[graph_builder] Creando constraints e índices ...")
        for sentencia in SETUP_CYPHER.strip().split(";"):
            sentencia = sentencia.strip()
            if sentencia:
                session.run(sentencia)

        # Cargar cada extracción
        for i, ext in enumerate(extracciones):
            ua = ext.unidad_archivistica
            fuente_id = ua.fragmento_id
            print(f"  [{i+1:02d}/{len(extracciones)}] Cargando folio ~{ua.folio} ...")

            session.execute_write(_merge_fuente, ua)
            contadores["fuentes"] += 1

            for actor in ext.actores:
                session.execute_write(_merge_actor, actor, fuente_id)
                contadores["actores"] += 1

            for lugar in ext.lugares:
                session.execute_write(_merge_lugar, lugar, fuente_id)
                contadores["lugares"] += 1

            for obj in ext.objetos:
                session.execute_write(_merge_objeto, obj, fuente_id)
                contadores["objetos"] += 1

            for evento in ext.eventos_institucionales_probados:
                session.execute_write(_merge_evento_institucional, evento, fuente_id)
                contadores["eventos_inst"] += 1

            for afirm in ext.afirmaciones:
                session.execute_write(_merge_afirmacion, afirm, fuente_id)
                contadores["afirmaciones"] += 1

    driver.close()

    print(f"\n[graph_builder] ✓ Carga completa en Neo4j:")
    print(f"  FuentesArchivisticas : {contadores['fuentes']}")
    print(f"  Actores              : {contadores['actores']}")
    print(f"  Lugares              : {contadores['lugares']}")
    print(f"  ObjetosBienes        : {contadores['objetos']}")
    print(f"  EventosInstitucional : {contadores['eventos_inst']}")
    print(f"  AfirmacionesHist.    : {contadores['afirmaciones']}")

    return contadores


# =====================================================================
# EXPORTAR A JSON (respaldo / inspección sin Neo4j)
# =====================================================================

def extracciones_a_grafo_json(extracciones: list[ExtraccionFolio]) -> dict:
    """Convierte extracciones a un dict de nodos/aristas para inspección o Gephi."""
    nodos: dict[str, dict] = {}
    aristas: list[dict] = []

    def nodo(id_, etiqueta, props):
        nodos[id_] = {"id": id_, "etiqueta": etiqueta, **{k: v for k, v in props.items() if v is not None}}

    def arista(origen, destino, tipo, props=None):
        aristas.append({"origen": origen, "destino": destino, "tipo": tipo, **(props or {})})

    for ext in extracciones:
        ua = ext.unidad_archivistica
        fid = ua.fragmento_id
        nodo(fid, "FuenteArchivistica", {"fondo": ua.fondo, "serie": ua.serie, "legajo": ua.legajo, "expediente": ua.expediente, "folio": ua.folio})

        for a in ext.actores:
            nodo(a.id_canonico, "Actor", {"nombre": a.nombre_principal, "variantes": a.variantes_ortograficas, "tipo": a.tipo_actor, "condicion": a.condicion_socioetnica, "cargos": a.cargos_mencionados})
            arista(a.id_canonico, fid, "MENCIONADO_EN")

        for l in ext.lugares:
            nodo(l.id, "Lugar", {"nombre": l.nombre_mencionado, "tipo": l.tipo_lugar, "jurisdiccion": l.jurisdiccion_superior})
            arista(l.id, fid, "MENCIONADO_EN")

        for o in ext.objetos:
            oid = f"objeto_{o.id}"
            nodo(oid, "ObjetoBien", {"descripcion": o.descripcion, "tipo": o.tipo_bien, "cantidad": o.cantidad_o_valor})
            arista(oid, fid, "MENCIONADO_EN")

        for ev in ext.eventos_institucionales_probados:
            nodo(ev.id, "EventoInstitucional", {"tipo": ev.tipo_evento, "categoria": ev.categoria_tematica, "fecha": ev.fecha_mencionada, "lugar": ev.lugar})
            for p in ev.participantes:
                arista(p.actor_id, ev.id, "PARTICIPA_EN", {"rol": p.rol})
            if ev.lugar:
                arista(ev.id, ev.lugar, "OCURRE_EN")
            for obj in ev.objetos_involucrados:
                arista(ev.id, f"objeto_{obj.id}", "INVOLUCRA_BIEN")

        for af in ext.afirmaciones:
            ev = af.evento_descrito
            nodo(ev.id, "EventoTestimoniado", {"tipo": ev.tipo_evento, "fecha_alegada": ev.fecha_mencionada})
            nodo(af.id, "AfirmacionHistorica", {"tipo": af.tipo_declaracion, "estado": af.estado_epistemologico, "cita": af.cita_textual_evidencia[:150], "folio": af.folio, "confianza": af.confianza_extraccion})
            arista(af.declarante_id, af.id, "DECLARO")
            arista(af.id, ev.id, "DESCRIBE_EVENTO")
            arista(af.id, fid, "EXTRAIDO_DE")
            for p in ev.participantes:
                arista(p.actor_id, ev.id, "ROL_EN_EVENTO", {"rol": p.rol})
            if ev.lugar:
                arista(ev.id, ev.lugar, "OCURRE_EN")
            for obj in ev.objetos_involucrados:
                arista(ev.id, f"objeto_{obj.id}", "INVOLUCRA_BIEN")
            for otro in af.contradice_afirmacion_ids:
                arista(af.id, otro, "CONTRADICE")
            for otro in af.ratifica_afirmacion_ids:
                arista(af.id, otro, "RATIFICA")

    from collections import Counter
    conteo = Counter(n["etiqueta"] for n in nodos.values())
    return {"nodos": list(nodos.values()), "aristas": aristas, "resumen": {"total_nodos": len(nodos), "total_aristas": len(aristas), "por_etiqueta": dict(conteo)}}


def guardar_grafo_json(grafo: dict, ruta: str | Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(grafo, f, ensure_ascii=False, indent=2)
    print(f"[graph_builder] Respaldo JSON guardado en: {ruta}")


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    BASE     = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = BASE / "GRAFO_CONOCIMIENTOS_CUSCO" / "data"
    ruta_extracciones = DATA_DIR / "extracciones.jsonl"

    if not ruta_extracciones.exists():
        print(f"ERROR: No se encuentra {ruta_extracciones}")
        print("Ejecuta primero: python run.py")
        sys.exit(1)

    extracciones: list[ExtraccionFolio] = []
    with ruta_extracciones.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                extracciones.append(ExtraccionFolio.model_validate_json(linea))

    print(f"[graph_builder] {len(extracciones)} extracciones cargadas.")

    # Siempre exporta JSON como respaldo
    grafo = extracciones_a_grafo_json(extracciones)
    guardar_grafo_json(grafo, DATA_DIR / "grafo.json")

    # Carga en Neo4j si está configurado
    if os.environ.get("NEO4J_PASSWORD"):
        cargar_en_neo4j(extracciones)
    else:
        print("\nNeo4j no configurado. Añade NEO4J_PASSWORD al .env para cargar el grafo.")
