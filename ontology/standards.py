"""
Mapeo de Estándares Internacionales y Ontología Propia (OHAC)
Archivo Regional del Cusco - Fondo Intendencia

Este módulo define los identificadores de URI, prefijos y equivalencias
conceptuales reutilizadas de los estándares:
- RiC-O (Records in Contexts - Ontology, ICA)
- CIDOC CRM (ISO 21127, ICOM)
- PROV-O (Provenance Ontology, W3C)
- SKOS (Simple Knowledge Organization System, W3C)
- OHAC (Ontología Histórica del Archivo del Cusco - Ontología Propia)
"""

# Prefijos y Namespaces formales
NAMESPACES = {
    "rico": "https://www.ica.org/standards/RiC/ontology#",
    "crm": "http://www.cidoc-crm.org/cidoc-crm/",
    "prov": "http://www.w3.org/ns/prov#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ohac": "https://archivo-cusco.pe/ontology/ohac#",
    "data": "https://archivo-cusco.pe/recurso/"
}

# 1. Reutilización selectiva de RiC-O (Estructura Archivística)
RICO_MAPPING = {
    "RecordSet": {
        "uri": f"{NAMESPACES['rico']}RecordSet",
        "descripcion": "Conjunto de documentos: Fondo (Intendencia), Serie (Causas Criminales), Legajo o Expediente."
    },
    "Record": {
        "uri": f"{NAMESPACES['rico']}Record",
        "descripcion": "Unidad documental o testimonio procesal específico."
    },
    "RecordPart": {
        "uri": f"{NAMESPACES['rico']}RecordPart",
        "descripcion": "Parte física de un documento: Folio o fragmento textual de procedencia."
    },
    "isOrWasIncludedIn": {
        "uri": f"{NAMESPACES['rico']}isOrWasIncludedIn",
        "descripcion": "Relación jerárquica: Folio pertenece a Expediente, Expediente pertenece a Legajo."
    }
}

# 2. Reutilización selectiva de CIDOC CRM (Patrimonio y Eventos)
CIDOC_MAPPING = {
    "E21_Person": {
        "uri": f"{NAMESPACES['crm']}E21_Person",
        "descripcion": "Individuo histórico humano."
    },
    "E74_Group": {
        "uri": f"{NAMESPACES['crm']}E74_Group",
        "descripcion": "Colectivos humanos, corporaciones o familias."
    },
    "E53_Place": {
        "uri": f"{NAMESPACES['crm']}E53_Place",
        "descripcion": "Entidad geográfica, pueblo, doctrina, ciudad o edificio."
    },
    "E5_Event": {
        "uri": f"{NAMESPACES['crm']}E5_Event",
        "descripcion": "Suceso delimitado en tiempo y espacio (base de los acontecimientos históricos)."
    },
    "E70_Thing": {
        "uri": f"{NAMESPACES['crm']}E70_Thing",
        "descripcion": "Bienes materiales, propiedades o recursos en disputa."
    },
    "P11_had_participant": {
        "uri": f"{NAMESPACES['crm']}P11_had_participant",
        "descripcion": "Relación de participación entre un actor y un evento."
    },
    "P7_took_place_at": {
        "uri": f"{NAMESPACES['crm']}P7_took_place_at",
        "descripcion": "Relación espacial: el evento ocurrió en un lugar."
    }
}

# 3. Reutilización selectiva de PROV-O (Procedencia del Dato)
PROV_MAPPING = {
    "wasDerivedFrom": {
        "uri": f"{NAMESPACES['prov']}wasDerivedFrom",
        "descripcion": "Enlace inquebrantable de una afirmación o hecho extraído hacia el fragmento/folio de evidencia."
    },
    "wasAttributedTo": {
        "uri": f"{NAMESPACES['prov']}wasAttributedTo",
        "descripcion": "Actor histórico o testigo que emitió la declaración."
    }
}

# 4. Reutilización selectiva de SKOS (Etiquetas y Variantes)
SKOS_MAPPING = {
    "prefLabel": {
        "uri": f"{NAMESPACES['skos']}prefLabel",
        "descripcion": "Nombre canónico principal normalizado (ej. 'Manuel Huancachoque')."
    },
    "altLabel": {
        "uri": f"{NAMESPACES['skos']}altLabel",
        "descripcion": "Variantes ortográficas históricas encontradas en el manuscrito ('Guancachoque', 'Mancachoque')."
    },
    "Concept": {
        "uri": f"{NAMESPACES['skos']}Concept",
        "descripcion": "Categorías controladas para tipos de eventos, roles y cargos."
    }
}

# 5. Extensiones Propias OHAC (Gaps Andino-Coloniales y Epistemológicos)
OHAC_EXTENSIONS = {
    "Ayllu": {
        "uri": f"{NAMESPACES['ohac']}Ayllu",
        "padre": "crm:E74_Group",
        "descripcion": "Unidad socio-territorial andina con autoridades comunales tradicionales."
    },
    "CondicionTributaria": {
        "uri": f"{NAMESPACES['ohac']}CondicionTributaria",
        "padre": "skos:Concept",
        "valores": ["IndioOriginario", "IndioForastero", "IndioTributario", "Reservado", "EspanolVecino", "Mestizo"]
    },
    "CargoVirreinal": {
        "uri": f"{NAMESPACES['ohac']}CargoVirreinal",
        "padre": "skos:Concept",
        "valores": [
            "CaciquePrincipal", "CaciqueRecaudador", "Segunda", "AlcaldeDeIndios",
            "ProtectorDeNaturales", "Subdelegado", "Corregidor", "Escribano", "Milicia"
        ]
    },
    "AfirmacionHistorica": {
        "uri": f"{NAMESPACES['ohac']}AfirmacionHistorica",
        "descripcion": "Reificación epistémica de testimonios para distinguir acusaciones/sospechas de hechos verificados."
    },
    "contradice": {
        "uri": f"{NAMESPACES['ohac']}contradice",
        "descripcion": "Relación que conecta dos afirmaciones con contenidos o testimonios incompatibles."
    },
    "ratifica": {
        "uri": f"{NAMESPACES['ohac']}ratifica",
        "descripcion": "Relación que conecta un testimonio que confirma o apoya a otro."
    },
    "desmiente": {
        "uri": f"{NAMESPACES['ohac']}desmiente",
        "descripcion": "Resolución o prueba concluyente que anula la veracidad de una queja o testimonio previo."
    }
}
