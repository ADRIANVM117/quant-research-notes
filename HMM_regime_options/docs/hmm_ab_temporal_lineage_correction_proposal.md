# Propuesta separada — corrección del linaje temporal HMM A/B

Fecha: 2026-09-26  
Estado: propuesta de corrección; no modifica ni sustituye el análisis exploratorio publicado.

## Hallazgo que motiva la propuesta

La auditoría de `hmm_exploratory_ab.py` verificó que los P90 publicados se generaron así: escalar con desarrollo, seleccionar semilla en desarrollo, reajustar el HMM con 2020–2026, calcular scores predictivos incluso para 2020–2023 con ese reajuste y tomar el P90 sobre esas fechas. Por tanto, los parámetros usados para los scores de desarrollo ya incorporaban 2024–2026.

Los artefactos originales se conservan y se denominan afectados por este linaje: sus P90, alertas y métricas dependientes no se sobrescriben.

## Corrección propuesta para una nueva variante

Para cada modelo A y B, y sin cambiar el conjunto de variables:

1. Calcular medias y desviaciones de escalamiento solo en desarrollo.
2. Ajustar las diez semillas solo en desarrollo y elegir la de mayor log-verosimilitud de desarrollo, con empate por semilla menor.
3. Congelar el modelo correspondiente a esa semilla **ajustado solo hasta el fin de desarrollo**. Identificar allí el estado descriptivo de mayor volatilidad.
4. Generar scores filtrados y predictivos de desarrollo con ese modelo congelado; fijar el P90 en las fechas comunes A/B de desarrollo.
5. Aplicar el mismo modelo, escalamiento, mapeo de estado y P90 a los tramos posteriores, sin reajuste ni recalibración.
6. Reportar por separado cobertura perdida por skew, calidad y toda alerta no disponible. Mantener las reglas vigentes de episodios, acreditación y censura.

Un eventual esquema de reentrenamiento expansivo o rodante debe ser una hipótesis distinta: fecha de cada reajuste, ventana de ajuste, reidentificación/alineación de estados y umbral deben predefinirse antes de evaluar resultados. No se puede introducir para reemplazar retrospectivamente el análisis actual.

## Alcance y límites

Esta propuesta no ejecuta nuevos resultados ni modifica umbrales publicados. Aunque se implemente, 2020–2026 seguiría siendo exploratorio por haber sido visto; la disponibilidad EOD antes de abrir `t+1` continúa como supuesto no verificado. No autoriza integración con Actinver.
