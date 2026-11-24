# Momentum Systematic Strategies

Este proyecto reúne líneas de investigación independientes sobre momentum: desde señales basadas en retornos históricos del propio activo hasta modelos sistemáticos que incorporan proxies factoriales y representaciones dinámicas de sus exposiciones. Cada línea conserva su pregunta, supuestos y límites; la infraestructura de datos diaria es común.

## Líneas de investigación

| Línea | Propósito |
| --- | --- |
| [01 — Time-Series Momentum](01_tsmom/) | Estudia la persistencia de los retornos propios de un activo; es el antecedente de investigación temporal. |
| [02 — Factor Momentum](02_factor_momentum/README.md) | Examina atribución con proxies factoriales, señales sistemáticas long/cash y la candidata exploratoria XLE. |
| [03 — Regime-aware Momentum](03_regime_aware_momentum/) | Investiga estabilidad de betas, incertidumbre de atribución y posibles cambios estructurales con OLS rolling, Kalman y diagnósticos online. |

Las líneas Deep Momentum Networks y Momentum Transformer permanecen como posibles direcciones futuras; no existen aún como subcarpetas de investigación en este proyecto.

## Datos e infraestructura compartida

El flujo diario común es: Alpha Vantage → [data_ingest/](data_ingest/) → Silver → [data_quality/](data_quality/) → Gold → notebooks de investigación.

La investigación consume series Gold validadas desde [`data/gold/daily_series/`](data/gold/daily_series/). Los siete ETFs empleados por Factor Momentum ya están versionados en Git; Gold no es, por tanto, una colección íntegramente ignorada por Git. Las capas raw y Silver siguen siendo etapas operativas del pipeline, no fuentes paralelas de análisis.

El alcance inicial es diario. La infraestructura intradía no forma parte de estas líneas de investigación actuales.
