# 02 — Factor Momentum

Esta línea estudia si parte del momentum observado en activos puede entenderse a través de la persistencia temporal de exposiciones económicas o grupos sistemáticos observables.

## Pregunta de investigación

¿Hasta qué punto el momentum observado en activos puede explicarse por momentum persistente en factores sistemáticos?

El marco conceptual es:

$ R_{i,t} = \sum_{k=1}^{K} \beta_{ik} F_{k,t} + \epsilon_{i,t} $

Aquí, $F_{k,t}$ representa retornos de factores sistemáticos, $\beta_{ik}$ la exposición del activo a esos factores y $\epsilon_{i,t}$ su componente idiosincrático. Es una hipótesis de investigación: todavía no se afirma que estos factores expliquen los activos del universo.

## Alcance inicial

La primera etapa no usa acciones individuales ni factores académicos puros. Utiliza ETFs líquidos como proxies observables de exposiciones económicas o factoriales; no se les atribuye una exposición factorial exacta.

| Proxy ETF | Lectura económica orientativa | Catálogo | Silver | Gold |
| --- | --- | --- | --- | --- |
| SPY | mercado amplio | Sí | Sí | Sí |
| QQQ | sesgo growth / large-cap technology | Sí | Sí | Sí |
| IWM | small-cap | No | No | No |
| IWD | value tilt | No | No | No |
| IWF | growth tilt | No | No | No |
| XLE | sector energía | Sí | Sí | Sí |
| XLF | sector financiero | Sí | Sí | No |

Disponibilidad verificada el 2026-11-19. `XLF` puede validarse y promoverse desde su Silver existente. Para `IWM`, `IWD` e `IWF` primero habrá que incorporarlos mediante el pipeline diario; no se descargó ninguna serie en esta preparación.

## Datos y reproducción

Los notebooks de esta línea consumirán exclusivamente:

`data/gold/daily_series/etf/<SYMBOL>.parquet`

No deben leer raw, Silver, `series/` ni datos intradía. Silver se consulta aquí sólo para inventario de disponibilidad.

Para validar y promover el Silver existente de XLF a Gold:

```powershell
python data_quality/validate_daily_sanity.py --asset-class etf --symbol XLF
```

Para producir Silver, validarlo y promoverlo para un proxy faltante:

```powershell
python data_ingest/run_daily_pipeline.py --symbol IWM --asset-class etf --expected-session-date YYYY-MM-DD
```

Sustituir `IWM` por `IWD` o `IWF` según corresponda y usar la última sesión estadounidense completada como fecha esperada.

## Relación con TSMOM

`01_tsmom` ya construyó un baseline de momentum temporal: pregunta si un activo sube o baja respecto a su propia historia. Esta línea no lo reemplaza. Pregunta, en cambio, si ese momentum coincide con persistencia en proxies de factores o grupos sistemáticos.

Por ahora no se extrae código compartido: la relación queda documentada y cada línea mantiene su notebook de investigación.

## Próximo laboratorio

`notebooks/01_factor_momentum_foundations.ipynb` define el universo proxy, los retornos de factores, el momentum de esos proxies y la futura comparación con momentum de activos. Aún no implementa regresiones, betas, PCA, señales, backtests, volatility targeting, construcción de cartera ni modelos de machine learning.
