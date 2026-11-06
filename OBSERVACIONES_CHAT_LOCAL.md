# Observaciones del chat GraphRAG local

## Alcance de esta etapa

Esta etapa conecta Gemini con el grafo Neo4j local mediante recuperación
estructurada. No corrige la ontología completa, no sincroniza `data/grafo.json`
con Neo4j, no añade embeddings, no incorpora OpenRouter y no prepara despliegue
web.

## Arquitectura observada

El flujo implementado es:

1. Gemini clasifica la pregunta en una intención y un término.
2. El código selecciona una consulta Cypher fija y parametrizada.
3. Neo4j recupera fuentes, folios, citas y estados epistemológicos.
4. Gemini redacta usando únicamente la evidencia recuperada.

Por tanto, es un GraphRAG controlado con enrutamiento de intención y recuperación
determinista. Gemini no escribe ni ejecuta Cypher arbitrario y las consultas del
chat son de solo lectura.

## Cambios implementados

- Chat local ejecutable con `python -m chat`.
- Intención específica para acusados y denunciados mediante `ROL_EN_EVENTO`.
- Recuperación de eventos por tipo, fecha alegada y lugares conectados mediante
  `OCURRE_EN`.
- Fallback a `gemini-flash-lite-latest` cuando el modelo principal devuelve un
  error de servidor.
- AFC deshabilitado explícitamente porque el chat no usa herramientas Gemini.
- Evidencias con fuente, folio, expediente, cita y estado epistemológico.
- Evaluación reproducible con diez preguntas basadas en el expediente 18.

## Evidencia recuperada

La evaluación contra Neo4j pasó los diez casos:

```text
10 passed
```

Los casos cubren:

- Tinta en 1806.
- Andrés Chuquitapa como acusado o denunciado.
- Tributarios ocultos.
- Manuel Huancachoque.
- Miguel Orey.
- Denuncias ante la Real Hacienda.
- Ayllu Tinta.
- Declaraciones de Isidro Cano.
- Resolución sobre las quejas.
- Tributarios descubiertos en el Ayllu Tinta.

Esto demuestra que el grafo contiene evidencia recuperable para esos casos con
los planes de consulta actualmente definidos. No demuestra que toda pregunta
libre sea recuperada correctamente.

## Evaluación real del LLM

Se ejecutaron los diez casos con Gemini y se validó que cada respuesta tuviera
evidencia, entidades y estados esperados.

Resultado observado:

```text
4 casos aprobados
6 casos fallidos
```

Los fallos observados se concentraron en:

- Clasificación de preguntas sobre tributarios.
- Preguntas sobre el Ayllu Tinta.
- Resoluciones oficiales.
- Cantidades como los 44 tributarios.
- Actores recuperados como menciones sin suficiente contexto narrativo.
- Respuestas que omitieron nombres o hechos centrales aunque existiera
  evidencia parcial.

Estos fallos no prueban que el grafo sea incorrecto. Indican que el enrutamiento,
la consulta o la redacción todavía no son suficientemente consistentes para
afirmar que el chat responde verídicamente a cualquier pregunta.

## Comportamiento epistemológico

Las respuestas deben distinguir entre:

- `Alegato_No_Comprobado`.
- `Confirmado_Oficial`.
- `Desmentido_Falso`.
- `En_Disputa`.

Una acusación o testimonio no debe presentarse como hecho confirmado. En las
pruebas de Tinta, por ejemplo, las quejas aparecen acompañadas por resoluciones
clasificadas como `Desmentido_Falso`; la respuesta debe conservar esa diferencia.

## Incidencias conocidas

- Gemini puede devolver `503 UNAVAILABLE` por saturación temporal. El chat usa
  un modelo de respaldo y muestra una advertencia.
- El SDK puede emitir warnings deprecados no relacionados con AFC; el AFC del
  chat ya está deshabilitado explícitamente.
- La salida de consola puede repetir muchas evidencias equivalentes.
- Algunas relaciones del grafo producen menciones de actores sin cita o estado
  epistemológico.
- La clasificación depende todavía de una llamada al LLM y puede escoger una
  intención demasiado general.

## Comandos de verificación

Suite normal:

```bash
python -m pytest
```

Evaluación de recuperación, sin consumir Gemini:

```bash
python -m pytest \
  tests/test_chat_evaluation.py::test_corpus_case_retrieves_expected_evidence -q
```

Evaluación live del LLM:

```bash
RUN_LIVE_CHAT_EVAL=1 python -m pytest \
  tests/test_chat_evaluation.py::test_live_llm_answer_is_grounded -q
```

## Próximo trabajo recomendado

Antes de añadir nuevas capacidades se debe corregir la recuperación de los seis
casos live fallidos. La prioridad es:

1. Recuperar contexto completo de actores y eventos.
2. Separar consultas de cantidades y resoluciones oficiales.
3. Relacionar de forma explícita Ayllu Tinta, tributarios y fuentes.
4. Deduplicar evidencias antes de enviarlas a Gemini.
5. Repetir la evaluación live y conservar los fallos como regresiones.

