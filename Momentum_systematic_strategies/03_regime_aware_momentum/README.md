# Regime-aware Momentum

Esta línea investiga la estabilidad temporal de las exposiciones factoriales, la incertidumbre asociada a su estimación y la identificación de posibles cambios estructurales en los retornos de activos financieros.

El objetivo es comprender las **limitaciones de los modelos con parámetros históricos o dinámicos** y determinar qué información adicional podría aportar una representación consciente de cambios de régimen.

La investigación parte de [`02_factor_momentum`](../02_factor_momentum/), sin asumir que una variación de las betas implica un régimen discreto ni que una mejora estadística necesariamente produce mayor rentabilidad.

## Research methodology

- **Activos:** QQQ, XLE y XLF.
- **Factores:** MKT, SIZE y GV, construidos mediante proxies ETF.
- **Benchmark:** rolling OLS de 252 sesiones.
- **Modelos dinámicos:** Kalman con incertidumbre fija y adaptativa.
- **Diagnósticos:** estabilidad de betas, errores de atribución, incertidumbre probabilística y posibles cambios estructurales.
- **Datos:** series diarias Gold de Alpha Vantage, 2018–2026.
- **Evaluación:** estimaciones causales con coeficientes disponibles hasta la sesión anterior.

Se utilizan observaciones comunes y especificaciones comparables para distinguir mejoras de atribución, calibración de incertidumbre y capacidad de detección.

## Research notebooks

| Notebook | Objetivo |
|---|---|
| [01 — Factor Stability Diagnostics](notebooks/01_factor_stability_diagnostics.ipynb) | Examinar cambios en betas, varianza sistemática y errores de atribución. |
| [02 — Dynamic Beta Estimation](notebooks/02_dynamic_beta_estimation.ipynb) | Comparar rolling OLS 252d frente a Kalman con parámetros fijos. |
| [03 — Adaptive Observation Uncertainty](notebooks/03_adaptive_observation_uncertainty.ipynb) | Evaluar incertidumbre adaptativa mediante EWMA y calibración probabilística. |
| [04 — Structural Change Diagnostics](notebooks/04_structural_change_diagnostics.ipynb) | Identificar episodios de inestabilidad factorial y distinguir alertas persistentes de efectos de solapamiento. |
| [05 — Online Changepoint Detection](notebooks/05_online_changepoint_detection.ipynb) | Evaluar BOCPD mediante datos históricos y simulaciones con cambios conocidos. |

## Key findings

**Factor stability.** La atribución factorial de XLE se deterioró entre 2019–2022 y 2023–2026 (R² OOS: 0.645 → 0.284). La varianza sistemática disminuyó proporcionalmente más que la varianza del error, mientras que las exposiciones a los factores también mostraron cambios estadísticamente relevantes bajo el análisis exploratorio.

**Dynamic beta estimation.** Kalman con parámetros fijos produjo mejoras modestas frente a rolling OLS. En XLE, durante 2022–2026, el R² OOS aumentó de 0.3164 a 0.3351, con pequeñas reducciones de MAE, RMSE y errores extremos. La mayor adaptabilidad no demostró una ventaja suficientemente grande para sustituir automáticamente el benchmark.

**Adaptive uncertainty.** Un \(R_t\) dinámico estimado mediante EWMA de innovaciones no mejoró consistentemente la atribución puntual. Sin embargo, redujo la pérdida logarítmica gaussiana y mejoró algunas propiedades de calibración probabilística, particularmente en XLE durante 2022.

**Structural instability.** Los diagnósticos detectaron episodios de errores asociados persistentemente con MKT. No obstante, el solapamiento de ventanas y la concentración de contribuciones en pocas sesiones limitaron su interpretación como evidencia de rupturas estructurales. Kalman tampoco superó uniformemente a OLS después de las alertas.

**Online changepoint detection.** La especificación BOCPD evaluada no produjo alertas durante 2022–2026. En simulaciones controladas, identificó únicamente 7 de 50 cambios persistentes de media de +2 desviaciones estándar dentro de 63 sesiones. Su sensibilidad resultó insuficiente para interpretar la ausencia de alertas históricas como evidencia de estabilidad.

## Interpretation and limitations

Los resultados permiten distinguir tres problemas que requieren tratamientos potencialmente diferentes: estimación de exposiciones cambiantes, representación de incertidumbre residual y detección de rupturas estructurales.

- La atribución utiliza factores contemporáneos realizados; no constituye un pronóstico del retorno del activo antes de la sesión.
- Las comparaciones son causales, pero el historial ya fue explorado y los resultados no representan una validación confirmatoria independiente.
- Los errores de atribución pueden reflejar betas desactualizadas, factores omitidos o shocks residuales; no identifican por sí solos un mecanismo único.
- Los diagnósticos de cambios estructurales no proporcionan fechas verificadas de ruptura. La especificación BOCPD actual queda como experimento documentado, no como detector operativo.
- Todavía no se ha demostrado que incorporar estimadores dinámicos o detección de cambios mejore una política de momentum en términos de rentabilidad o control de riesgo.

## Research outlook

La siguiente etapa estudiará si una política de momentum puede aprovechar información temporal y condiciones de mercado de manera más flexible que las reglas clásicas.

Las **Deep Momentum Networks** constituyen una hipótesis de investigación posterior, no una solución previamente validada. Su contribución deberá evaluarse frente a baselines sistemáticos interpretables, con validación cronológica, control de complejidad y costes de operación.

## Data

Todas las investigaciones consumen exclusivamente series validadas desde:

`data/gold/daily_series/etf/<SYMBOL>.parquet`

La infraestructura de ingesta y calidad es compartida por `Momentum_systematic_strategies/`. Las notebooks no modifican los archivos Gold.