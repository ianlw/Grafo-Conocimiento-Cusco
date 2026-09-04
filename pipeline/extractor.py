"""
Extractor LLM de Entidades y Afirmaciones Históricas
======================================================
Toma cada SegmentoFolio producido por segmenter.py y solicita al LLM
que devuelva una ExtraccionFolio validada contra la ontología OHAC.

Usa el SDK oficial de Google GenAI (google-genai) con output JSON estructurado.
Requiere la variable de entorno GOOGLE_API_KEY.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from ontology.models import ExtraccionFolio
from pipeline.segmenter import SegmentoFolio, segmentar_expediente

# Certificados SSL del sistema (necesarios en redes con proxy corporativo)
_CERT_PATH = _ROOT / "certs_windows.pem"
if _CERT_PATH.exists():
    os.environ.setdefault("GRPC_DEFAULT_SSL_ROOTS_FILE_PATH", str(_CERT_PATH))
    os.environ.setdefault("SSL_CERT_FILE", str(_CERT_PATH))
    os.environ.setdefault("REQUESTS_CA_BUNDLE", str(_CERT_PATH))

# Modelo confirmado disponible con esta API key
MODELO_ID = "gemini-3.6-flash"

# =====================================================================
# PROMPT DE SISTEMA
# =====================================================================

SYSTEM_PROMPT = """
Eres un experto historiador y analista de documentos judiciales del Archivo Regional del Cusco
(Perú, período virreinal tardío, 1780-1824). Tu tarea es extraer entidades y relaciones históricas
del texto que se te proporciona.

REGLAS ABSOLUTAS:
1. NUNCA registres acusaciones, sospechas o testimonios como hechos verificados.
   Toda afirmación subjetiva debe encapsularse en un objeto "AfirmacionHistorica"
   con su tipo_declaracion, estado_epistemologico y cita_textual_evidencia obligatoria.

2. La cita_textual_evidencia es OBLIGATORIA. Debe ser una cita literal del texto fuente
   de al menos 10 caracteres. Sin cita, no hay afirmación.

3. Los nombres de personas tienen ortografía muy inestable en el siglo XIX colonial.
   Registra TODAS las variantes encontradas en variantes_ortograficas.

4. Solo devuelve el JSON. Sin explicaciones, sin markdown, sin texto adicional.
   El JSON debe validar contra el esquema ExtraccionFolio.

CLASES DE ACTORES COLONIALES ANDINOS:
- condicion_socioetnica: IndioOriginario, IndioForastero, IndioTributario, Reservado,
  EspanolVecino, Mestizo, Noble_Cacique, Eclesiástico, Desconocido
- cargos: CaciquePrincipal, CaciqueRecaudador, Segunda, AlcaldeDeIndios, ProtectorDeNaturales,
  Subdelegado, Corregidor, Escribano, Sargento, Teniente, Soldado, Fiscal

TIPOS DE DECLARACION:
- TestimonioDirecto: El declarante presenció directamente el hecho.
- Acusacion: Cargo formal o queja presentada ante autoridad.
- Sospecha: El declarante infiere o cree algo sin haberlo presenciado.
- ResolucionOficial: Sentencia, auto o dictamen de una autoridad.
- Confesion_Rectificacion: El declarante corrige o matiza una declaración previa.

ESTADOS EPISTEMOLOGICOS:
- Alegato_No_Comprobado: No hay resolución oficial que lo confirme ni lo desmienta.
- Confirmado_Oficial: Una resolución posterior lo confirma como verdadero.
- Desmentido_Falso: Una resolución lo declara falso o fabricado.
- En_Disputa: Hay testimonios contradictorios sin resolución final.
"""


def construir_prompt_usuario(segmento: SegmentoFolio, schema_json: str) -> str:
    return f"""
Analiza el siguiente fragmento documental del Expediente {segmento.expediente},
Legajo {segmento.legajo}, Folio aproximado {segmento.folio_estimado}.
Tipo de acto identificado: {segmento.tipo_acto_procesal}.

---TEXTO FUENTE---
{segmento.texto_original}
---FIN DEL TEXTO---

Devuelve UN ÚNICO objeto JSON que valide contra este esquema:
{schema_json}

El campo "unidad_archivistica" debe contener:
  - fondo: "Intendencia"
  - serie: "Causas Criminales"
  - legajo: {segmento.legajo}
  - expediente: {segmento.expediente}
  - folio: {segmento.folio_estimado}
  - fragmento_id: "{segmento.expediente_id}_f{segmento.folio_estimado:02d}_seg{segmento.numero_segmento:02d}"
  - texto_original: (el texto completo del segmento, tal cual)

Solo JSON puro. Sin markdown. Sin backticks. Sin texto antes o después del JSON.
"""


def extraer_segmento(
    segmento: SegmentoFolio,
    client,
    schema_json: str,
    max_retries: int = 4,
    delay: float = 15.0,
) -> Optional[ExtraccionFolio]:
    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError

    prompt = construir_prompt_usuario(segmento, schema_json)

    for intento in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODELO_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            texto = response.text.strip()

            # Limpia markdown accidental
            texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.MULTILINE)
            texto = re.sub(r"\s*```$", "", texto, flags=re.MULTILINE)

            datos = json.loads(texto)
            return ExtraccionFolio.model_validate(datos)

        except json.JSONDecodeError as e:
            print(f"    [extractor] ERROR JSON (intento {intento+1}): {e}")
        except ValidationError as e:
            print(f"    [extractor] ERROR Pydantic (intento {intento+1}): {e.error_count()} errores")
            for err in e.errors()[:3]:
                print(f"      -> {err['loc']}: {err['msg']}")
        except ClientError as e:
            print(f"    [extractor] Quota/Rate Limit (intento {intento+1}): {e.message[:100] if hasattr(e, 'message') else str(e)[:100]}", flush=True)
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                espera = 20.0 * (intento + 1)
                print(f"    [extractor] Esperando {espera}s por cuota Free-Tier...", flush=True)
                time.sleep(espera)
                continue
        except Exception as e:
            msg = str(e)
            print(f"    [extractor] ERROR ({type(e).__name__}): {msg[:120]}", flush=True)
            if "503" in msg or "UNAVAILABLE" in msg or "high demand" in msg:
                espera = 15.0 * (intento + 1)
                print(f"    [extractor] Servidor ocupado (503). Esperando {espera}s...", flush=True)
                time.sleep(espera)
                continue

        if intento < max_retries:
            time.sleep(delay)

    return None


def run_extraccion_completa(
    ruta_transcripcion: str | Path,
    ruta_salida_jsonl: str | Path,
    pausa_entre_segmentos: float = 3.5,
    forzar_reextraccion: bool = False,
) -> list[ExtraccionFolio]:
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY no encontrada.\n"
            "Añádela al archivo .env: GOOGLE_API_KEY=tu_clave"
        )

    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    schema_json = json.dumps(ExtraccionFolio.model_json_schema(), ensure_ascii=False, indent=2)
    segmentos = segmentar_expediente(ruta_transcripcion)

    print(f"[extractor] {len(segmentos)} segmentos | modelo: {MODELO_ID}", flush=True)

    ruta_salida = Path(ruta_salida_jsonl)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Si se fuerza reextracción, borrar el archivo previo
    if forzar_reextraccion and ruta_salida.exists():
        ruta_salida.unlink()

    # Cargar extracciones ya existentes si no se fuerza la reextracción
    existentes: dict[str, ExtraccionFolio] = {}
    if ruta_salida.exists() and not forzar_reextraccion:
        with ruta_salida.open("r", encoding="utf-8") as f_in:
            for linea in f_in:
                linea = linea.strip()
                if linea:
                    try:
                        ext = ExtraccionFolio.model_validate_json(linea)
                        existentes[ext.unidad_archivistica.fragmento_id] = ext
                    except Exception:
                        pass
        if existentes:
            print(f"[extractor] Reutilizando {len(existentes)} segmentos ya extraidos previamente.", flush=True)

    extracciones: list[ExtraccionFolio] = []
    errores = 0

    for i, segmento in enumerate(segmentos):
        frag_id = f"{segmento.expediente_id}_f{segmento.folio_estimado:02d}_seg{segmento.numero_segmento:02d}"
        print(
            f"\n[{i+1:02d}/{len(segmentos)}] Folio ~{segmento.folio_estimado:02d} "
            f"| {segmento.tipo_acto_procesal} | {segmento.longitud_chars} chars",
            flush=True
        )

        if frag_id in existentes and not forzar_reextraccion:
            print("    OK (reutilizado de sesion previa)", flush=True)
            extracciones.append(existentes[frag_id])
            continue

        extraccion = extraer_segmento(segmento, client, schema_json)

        if extraccion is not None:
            extracciones.append(extraccion)
            # Guardar incrementalmente de inmediato
            with ruta_salida.open("a", encoding="utf-8") as f_out:
                f_out.write(extraccion.model_dump_json(ensure_ascii=False) + "\n")
            print(
                f"    OK | actores={len(extraccion.actores)} "
                f"afirmaciones={len(extraccion.afirmaciones)} "
                f"eventos={len(extraccion.eventos_institucionales_probados)}",
                flush=True
            )
        else:
            errores += 1
            print(f"    FALLO --- segmento {segmento.numero_segmento}", flush=True)

        if i < len(segmentos) - 1:
            time.sleep(pausa_entre_segmentos)

    print(f"\n{'='*55}", flush=True)
    print(f"  EXTRACCIÓN COMPLETADA: {len(extracciones)}/{len(segmentos)} OK | {errores} errores", flush=True)
    print(f"  Salida: {ruta_salida}", flush=True)
    print(f"{'='*55}", flush=True)

    return extracciones


if __name__ == "__main__":
    BASE = Path(__file__).resolve().parent.parent.parent
    run_extraccion_completa(
        ruta_transcripcion=BASE / "Transcripcion_CC_L14E18.txt",
        ruta_salida_jsonl=BASE / "GRAFO_CONOCIMIENTOS_CUSCO" / "data" / "extracciones.jsonl",
    )
