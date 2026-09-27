"""
Segmentador de Folios y Actos Procesales
=========================================
Divide el texto del expediente colonial en unidades procesables llamadas "segmentos".

Estrategia de segmentación detectada en el Expediente 18 (1806):
  - El símbolo '#' actúa como separador físico de folios/actos.
  - Algunas páginas incluyen marcadores explícitos como 'Folio 20', 'folio 28', 'Folio 33'.
  - Cada segmento se enriquece con metadatos: folio estimado, fecha detectada y tipo de acto procesal.
"""

import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Identificadores de tipos de acto procesal colonial basados en el corpus real
TIPOS_ACTO = {
    "certifico": "Certificacion_Testigo",
    "certificacion": "Certificacion_Testigo",
    "digo y certifico": "Certificacion_Testigo",
    "señor fiscal": "Dictamen_Fiscal",
    "fiscal": "Dictamen_Fiscal",
    "parezco y digo": "Queja_Memorial_Peticion",
    "pido y suplico": "Queja_Memorial_Peticion",
    "visto": "Auto_Decreto_Judicial",
    "auto": "Auto_Decreto_Judicial",
    "decreto": "Auto_Decreto_Judicial",
    "comparecio": "Declaracion_Judicial",
    "juramento": "Declaracion_Judicial",
    "prometo decir verdad": "Declaracion_Judicial",
    "informe": "Informe_Subdelegado",
    "resulta de ellas": "Informe_Subdelegado",
    "nota": "Nota_Escribano",
    "doy fe": "Accion_Notarial",
    "sello": "Encabezado_Protocolo",
}


@dataclass
class SegmentoFolio:
    """Unidad atómica de texto preparada para el extractor LLM."""
    expediente_id: str
    legajo: int
    expediente: int
    numero_segmento: int
    folio_estimado: Optional[int]
    folio_referencia_texto: Optional[str]   # Texto literal del marcador de folio si lo hay
    fecha_detectada: Optional[str]
    tipo_acto_procesal: str
    texto_original: str
    longitud_chars: int

    def to_dict(self) -> dict:
        return asdict(self)


def _detectar_folio_explicito(texto: str) -> tuple[Optional[int], Optional[str]]:
    """Busca marcadores de folio explícitos en el texto: 'Folio 20', 'folio 28', etc."""
    patron = re.search(r'\bfolio\s+(\d+)\b', texto, re.IGNORECASE)
    if patron:
        return int(patron.group(1)), patron.group(0)
    return None, None


def _detectar_fecha(texto: str) -> Optional[str]:
    """Extrae la primera referencia temporal del segmento."""
    # Fechas en formato colonial: 'primero de agosto de 1806', 'Agosto 26 de 1806', 'Setiembre. 17 de 1806'
    patrones = [
        r'\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b',
        r'\b\w+\s+\d{1,2}\s+de\s+\d{4}\b',
        r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|setiembre|septiembre'
        r'|octubre|noviembre|diciembre)\s+\d{1,2}\s+de\s+\d{4}\b',
    ]
    for p in patrones:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return None


def _detectar_tipo_acto(texto: str) -> str:
    """Clasifica el tipo de acto procesal basándose en palabras clave del corpus."""
    texto_lower = texto.lower()
    for clave, tipo in TIPOS_ACTO.items():
        if clave in texto_lower:
            return tipo
    return "Fragmento_No_Clasificado"


def segmentar_expediente(
    ruta_archivo: str | Path,
    legajo: int = 14,
    expediente: int = 18,
    expediente_id: str = "exp_ccc_14_18",
    min_chars: int = 80,
) -> list[SegmentoFolio]:
    """
    Lee el archivo de transcripción y lo divide en segmentos procesables.

    Args:
        ruta_archivo: Ruta al .txt de transcripción.
        legajo: Número de legajo del expediente.
        expediente: Número de expediente.
        expediente_id: ID canónico del expediente.
        min_chars: Segmentos con menos de este número de caracteres se descartan (encabezados vacíos).

    Returns:
        Lista de SegmentoFolio listos para ser enviados al extractor.
    """
    texto_completo = Path(ruta_archivo).read_text(encoding="utf-8", errors="replace")

    # El separador físico de folios/actos en el manuscrito transcrito es el símbolo '#'
    bloques_raw = re.split(r'\n\s*#\s*\n', texto_completo)

    segmentos: list[SegmentoFolio] = []
    folio_corriente = 1  # Folio estimado incremental cuando no hay marcador explícito

    for i, bloque in enumerate(bloques_raw):
        texto = bloque.strip()
        if len(texto) < min_chars:
            continue  # Descarta bloques de encabezado o separadores vacíos

        folio_explicito, folio_ref = _detectar_folio_explicito(texto)
        fecha = _detectar_fecha(texto)
        tipo_acto = _detectar_tipo_acto(texto)

        # Si hay un marcador de folio explícito lo usa, si no, incrementa el contador
        if folio_explicito is not None:
            folio_corriente = folio_explicito

        segmento = SegmentoFolio(
            expediente_id=expediente_id,
            legajo=legajo,
            expediente=expediente,
            numero_segmento=len(segmentos) + 1,
            folio_estimado=folio_corriente,
            folio_referencia_texto=folio_ref,
            fecha_detectada=fecha,
            tipo_acto_procesal=tipo_acto,
            texto_original=texto,
            longitud_chars=len(texto),
        )
        segmentos.append(segmento)

        # Incrementa folio estimado para el siguiente bloque si no hay marcador
        if folio_explicito is None:
            folio_corriente += 1

    return segmentos


def guardar_segmentos_json(
    segmentos: list[SegmentoFolio],
    ruta_salida: str | Path,
) -> None:
    """Persiste los segmentos como JSON con un elemento por línea (JSONL)."""
    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        for s in segmentos:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    print(f"[segmenter] {len(segmentos)} segmentos guardados en: {ruta}")


if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent

    ruta_transcripcion = BASE / "corpus" / "Transcripcion_CC_L14E18.txt"
    ruta_salida = BASE / "data" / "segmentos.jsonl"

    print(f"[segmenter] Leyendo: {ruta_transcripcion}")
    segmentos = segmentar_expediente(ruta_transcripcion)

    print(f"\n{'='*60}")
    print(f"  RESUMEN DE SEGMENTACIÓN — Expediente 18, Legajo 14")
    print(f"{'='*60}")
    for s in segmentos:
        print(
            f"  Segmento {s.numero_segmento:02d} | Folio ~{s.folio_estimado:02d} "
            f"| {s.tipo_acto_procesal:<32} | {s.longitud_chars:>5} chars"
            + (f" | Fecha: {s.fecha_detectada}" if s.fecha_detectada else "")
        )

    print(f"\n[segmenter] Total: {len(segmentos)} segmentos procesables")
    guardar_segmentos_json(segmentos, ruta_salida)
