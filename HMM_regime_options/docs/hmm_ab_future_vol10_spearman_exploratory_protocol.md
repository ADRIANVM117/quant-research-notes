# Protocolo — evaluación exploratoria de volatilidad futura a 10 sesiones

Fecha: 2026-09-27  
Estado: fijado antes de ejecutar una única evaluación histórica exploratoria.

## Datos y muestra común

La fuente será `reports/hmm_ab_development_frozen_scores_future_vol10_2024_2026.csv`. Se usarán exclusivamente filas con `future_vol10_eligible=True`, `future_vol10` no faltante y valores no faltantes de los tres predictores: `vol20_t`, `A_predictive_risk_next` y `B_predictive_risk_next`. Esa misma muestra y esos mismos índices se usarán para las tres correlaciones y en cada réplica bootstrap.

Los scores A/B ya estaban congelados con parámetros, escalamiento y selección de semilla de desarrollo; este protocolo no reajusta HMM, no modifica scores y no crea umbrales, alertas o episodios.

## Estadísticos principales

Se calcularán correlaciones de Spearman entre `future_vol10` y, por separado:

1. `vol20_t`;
2. `A_predictive_risk_next`;
3. `B_predictive_risk_next`.

Las comparaciones principales son `rho_A - rho_vol20` y `rho_B - rho_A`.

## Incertidumbre exploratoria por solapamiento

Las ventanas futuras de diez sesiones se solapan. Se usará bootstrap móvil de bloques consecutivos de **20 decisiones**, sin envoltura circular: en cada réplica se toman bloques cuyo inicio se elige uniformemente entre los índices `0` y `n-20`, se concatenan hasta alcanzar `n` observaciones y se recortan a `n`. Los mismos índices remuestreados se aplican simultáneamente a resultado y tres predictores.

Se fijan antes de ejecutar:

- semilla pseudoaleatoria: `20260927`;
- réplicas: `5000`;
- intervalos exploratorios: percentiles 2.5% y 97.5% de cada diferencia.

Un intervalo que incluya cero se interpreta exclusivamente como **inconcluso respecto a mejora**. No se traduce ninguna diferencia de correlación en utilidad económica.

## Alcance

2024–2026 es historia ya vista: el ejercicio es exploratorio y no una prueba prospectiva intacta. No evalúa alertas de caída, no aprueba modelos ni autoriza integración con Actinver.
