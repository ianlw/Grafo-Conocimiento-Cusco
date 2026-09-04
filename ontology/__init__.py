"""
Paquete de Ontología del Archivo Histórico del Cusco (OHAC)
"""

from .standards import (
    NAMESPACES,
    RICO_MAPPING,
    CIDOC_MAPPING,
    PROV_MAPPING,
    SKOS_MAPPING,
    OHAC_EXTENSIONS,
)
from .models import (
    UnidadArchivistica,
    Lugar,
    ObjetoOBien,
    ActorHistorico,
    Participacion,
    EventoHistorico,
    AfirmacionHistorica,
    ExtraccionFolio,
)

__all__ = [
    "NAMESPACES",
    "RICO_MAPPING",
    "CIDOC_MAPPING",
    "PROV_MAPPING",
    "SKOS_MAPPING",
    "OHAC_EXTENSIONS",
    "UnidadArchivistica",
    "Lugar",
    "ObjetoOBien",
    "ActorHistorico",
    "Participacion",
    "EventoHistorico",
    "AfirmacionHistorica",
    "ExtraccionFolio",
]
