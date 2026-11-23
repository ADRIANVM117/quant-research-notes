# Regime-aware Momentum

Esta línea investiga cómo cambian las exposiciones factoriales a través del tiempo, qué consecuencias tienen esos cambios sobre la atribución de retornos y si los modelos dinámicos representan mejor la incertidumbre que una estimación rolling convencional.

El objetivo es estudiar la **no estacionariedad de las relaciones factoriales**, sin asumir de antemano la existencia de regímenes discretos ni que una mejora estadística implique mayor rentabilidad.

## Research methodology

La investigación parte del modelo factorial desarrollado en [`02_factor_momentum`](../02_factor_momentum/), utilizando:

- **Activos:** QQQ, XLE y XLF.
- **Factores:** MKT, SIZE y GV, construidos con proxies ETF.
- **Benchmark:** rolling OLS de 252 sesiones.
- **Modelos dinámicos:** Kalman con incertidumbre fija y adaptativa.
- **Datos:** series diarias Gold de Alpha Vantage.
- **Evaluación:** atribución causal con coeficientes disponibles hasta la sesión anterior.

Las estimaciones dinámicas se comparan sobre observaciones comunes, conservando la misma estructura factorial.

## Research notebooks

| Notebook | Objetivo |
|---|---|
| [01 — Factor Stability Diagnostics](notebooks/01_factor_stability_diagnostics.ipynb) | Analizar cambios en betas, varianza sistemática y errores de atribución. |
| [02 — Dynamic Beta Estimation](notebooks/02_dynamic_beta_estimation.ipynb) | Comparar rolling OLS 252d frente a Kalman con parámetros fijos. |
| [03 — Adaptive Observation Uncertainty](notebooks/03_adaptive_observation_uncertainty.ipynb) | Evaluar incertidumbre residual dinámica y calibración probabilística. |
| `04_structural_change_diagnostics.ipynb` *(en desarrollo)* | Investigar posibles cambios estructurales y la respuesta de OLS y Kalman. |

## Key findings

**Factor stability.** XLE mostró un deterioro de atribución entre 2019–2022 y 2023–2026: su R² pasó de 0.645 a 0.284. La varianza sistemática disminuyó proporcionalmente más que la varianza del error, mientras que las exposiciones factoriales también presentaron cambios relevantes.

**Dynamic betas.** Kalman con parámetros fijos mejoró modestamente la atribución frente a rolling OLS. En XLE, durante la evaluación 2022–2026, el R² aumentó de 0.3164 a 0.3351, con pequeñas reducciones de MAE y errores extremos.

**Adaptive uncertainty.** Permitir que la incertidumbre de observación evolucione mediante EWMA no produjo mejoras consistentes en atribución puntual. Sin embargo, mejoró algunas propiedades de calibración probabilística, especialmente durante 2022.

Estos resultados motivan investigar si existen cambios persistentes o abruptos en las relaciones factoriales que los estimadores actuales representan con retraso.

## Interpretation and limitations

- Los retornos factoriales contemporáneos se utilizan para atribución, no para pronosticar anticipadamente los retornos del activo.
- Los cortes temporales y los modelos se han examinado retrospectivamente; los resultados no constituyen validación confirmatoria independiente.
- Una menor capacidad explicativa no demuestra por sí sola un cambio de régimen ni implica necesariamente una pérdida de utilidad económica de las señales de momentum.
- Ningún modelo dinámico se considera superior por su complejidad: su contribución debe evaluarse frente al benchmark y en términos de representación del riesgo.

## Data

Todas las investigaciones consumen exclusivamente series validadas desde:

`data/gold/daily_series/etf/<SYMBOL>.parquet`

La infraestructura de ingesta y calidad es compartida por `Momentum_systematic_strategies/`. Los notebooks no modifican los archivos Gold.