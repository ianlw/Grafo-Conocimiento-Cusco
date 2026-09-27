# Evaluación de Calidad de Construcción del Grafo de Conocimiento (KGCQ)

**Caso de Estudio:** Expediente 18, Legajo 14 (1806), Serie Causas Criminales, Fondo Intendencia del Archivo Regional del Cusco (ARC).  
**Metodología:** Inspirada en la evaluación formal de grafos de conocimiento generados por LLMs (*Ontology-grounded Automatic Knowledge Graph Construction by LLM*, Feng et al., KDD 2024).

---

## 🏆 Resumen Ejecutivo del Índice KGCQ

| Métrica Global | Valor | Grado | Diagnóstico |
| :--- | :---: | :---: | :--- |
| **Índice Compuesto KGCQ** | **94.1 / 100** | **A+** | Construcción sobresaliente: rigurosamente anclada al corpus y conformante al metamodelo ontológico. |

### Desglose de Sub-puntuaciones
* **Conformidad con el Metamodelo (25%):** `100.0%`
* **Fidelidad de Anclaje Textual (30%):** `99.0%`
* **Conectividad Estructural (20%):** `100.0%`
* **Canonicalización y Normalización SKOS (15%):** `63.0%`
* **Completitud y Reificación Epistémica (10%):** `100.0%`

---

## 1. Conformidad con el Metamodelo Ontológico

Evaluación del cumplimiento de las restricciones ontológicas basadas en **RiC-O**, **CIDOC CRM (ISO 21127)**, **PROV-O** y **OHAC**:

| Dimensión | Conteo | Porcentaje |
| :--- | :---: | :---: |
| **Nodos Totales ($|V|$)** | **259** | 100.0% |
| **Aristas Totales ($|E|$)** | **574** | 100.0% |
| **Integridad Referencial** | 574 / 574 | **100.0%** |
| **Conformidad Dominio / Rango** | 574 / 574 | **100.0%** |
| **Nodos Aislados (Grado = 0)** | 0 | 0.0% |

### Distribución de Nodos por Clase Ontológica
* **`:FuenteArchivistica`**: 21 (8.1%)
* **`:Actor`**: 89 (34.4%)
* **`:Lugar`**: 20 (7.7%)
* **`:ObjetoBien`**: 20 (7.7%)
* **`:EventoInstitucional`**: 27 (10.4%)
* **`:EventoTestimoniado`**: 48 (18.5%)
* **`:AfirmacionHistorica`**: 34 (13.1%)

### Distribución de Aristas por Tipo de Relación
* **`[:MENCIONADO_EN]`**: 193 (33.6%)
* **`[:PARTICIPA_EN]`**: 47 (8.2%)
* **`[:DECLARO]`**: 49 (8.5%)
* **`[:DESCRIBE_EVENTO]`**: 49 (8.5%)
* **`[:EXTRAIDO_DE]`**: 49 (8.5%)
* **`[:ROL_EN_EVENTO]`**: 106 (18.5%)
* **`[:OCURRE_EN]`**: 60 (10.5%)
* **`[:INVOLUCRA_BIEN]`**: 21 (3.7%)

---

## 2. Fidelidad de Anclaje Textual y Verificación de Citas (Grounding Veracity)

En concordancia con el principio de *ontology grounding* para mitigar alucinaciones de LLMs, cada afirmación testimonial extraída se valida contra el texto paleográfico original:

| Nivel de Anclaje | Citas | Porcentaje | Interpretación |
| :--- | :---: | :---: | :--- |
| **Coincidencia Exacta (100%)** | **32** | **65.3%** | Subcadena textual idéntica al manuscrito original. |
| **Anclaje Alto (>= 85%)** | **48** | **98.0%** | Cita fidedigna con variaciones menores de espaciado/puntuación paleográfica. |
| **Anclaje Medio (70% - 84%)** | **1** | **2.0%** | Cita con ligera paráfrasis o elisión textual. |
| **Riesgo de Alucinación (< 70%)** | **0** | **0.0%** | Testimonio no respaldado fehacientemente en la fuente. |

* **Total de Citas Evaluadas:** 49
* **Longitud Promedio de Evidencia:** 165.7 caracteres (Rango: [80 - 398])
* **Confianza Promedio del Extractor LLM:** 1.00 / 1.00

---

## 3. Canonicalización y Desambiguación de Entidades (SKOS)

Evaluación del tratamiento de la inestabilidad ortográfica colonial andina:

* **Actores Canónicos Registrados:** 89
* **Actores con Variantes Históricas (`altLabel`):** 84 (121 grafías registradas)
* **Factor de Consolidación de Superficie:** **2.36x** (unificación de variantes como *Huancachoque*, *Guancachoque*, *Mancachoque* en una sola entidad).
* **Tasa de Identificación Socioétnica:** **61.8%** (atribución explícita de *Indio Originario*, *Noble Cacique*, *Español Vecino*, etc.).
* **Tasa de Identificación de Cargos/Oficios:** **59.6%** (*Cacique Recaudador*, *Sargento de Milicias*, *Subdelegado*, etc.).

---

## 4. Análisis Epistémico y Crítica de Fuentes (OHAC)

Estructuración de testimonios y reificación para evitar el sesgo factual ingenuo:

* **Total Afirmaciones Reificadas:** 34
* **Tasa de Reificación con Evidencia Obligatoria:** **100.0%**

### Distribución por Estado Epistemológico
* **`Desmentido_Falso`**: 1 (2.9%)
* **`Alegato_No_Comprobado`**: 28 (82.4%)
* **`Confirmado_Oficial`**: 4 (11.8%)
* **`En_Disputa`**: 1 (2.9%)

### Distribución por Tipo de Declaración
* **`ResolucionOficial`**: 5 (14.7%)
* **`Acusacion`**: 18 (52.9%)
* **`Confesion_Rectificacion`**: 3 (8.8%)
* **`TestimonioDirecto`**: 7 (20.6%)
* **`Sospecha`**: 1 (2.9%)

* **Relaciones de Contradicción (`[:CONTRADICE]`):** 0
* **Relaciones de Ratificación (`[:RATIFICA]`):** 0

---

## 5. Topología de Red y Actores Históricos Centrales

* **Densidad del Grafo:** `0.01718`
* **Grado Promedio:** `4.43` aristas por nodo
* **Componentes Conexas:** `1` (Componente Gigante agrupa al `100.0%` de los nodos)

### Ranking de Centralidad de Grado (Top 10 Actores Clave)

| # | Actor | Condición / Tipo | Grado Total | Conexiones Entrantes | Conexiones Salientes |
| :-: | :--- | :--- | :-: | :-: | :-: |
| 1 | **Manuel Huancachoque** | Desconocido | 19 | 0 | 19 |
| 2 | **Manuel Huancachoque** | IndioTributario | 18 | 0 | 18 |
| 3 | **Manuel Huancachoque** | IndioTributario | 16 | 0 | 16 |
| 4 | **Andrés Chuquitapa** | Desconocido | 15 | 0 | 15 |
| 5 | **Isidro Cano** | Desconocido | 11 | 0 | 11 |
| 6 | **Chuquitapa** | No especificada | 11 | 0 | 11 |
| 7 | **Pedro de la Mata** | EspanolVecino | 9 | 0 | 9 |
| 8 | **Guancachoque** | IndioTributario | 8 | 0 | 8 |
| 9 | **Manuel Guancachoque** | IndioTributario | 8 | 0 | 8 |
| 10 | **Mariano Casorla** | EspanolVecino | 8 | 0 | 8 |

---
*Generado automáticamente por el motor de estadísticas KGCQ de Grafo de Conocimiento Histórico del Cusco.*
