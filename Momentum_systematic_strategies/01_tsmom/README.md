# 01 — Time-Series Momentum (TSMOM)

Laboratorio inicial para investigar momentum de series temporales con datos diarios. Esta carpeta sólo fija el alcance y el punto de partida; no contiene aún señal, backtest, métricas, configuraciones ni resultados.

## Alcance inicial

- Universo congelado: `SPY`, `QQQ`, `XLE`, `GLD`.
- Frecuencia: diaria.
- Fuente exclusiva: `../data/gold/daily_series/etf/<SYMBOL>.parquet`.
- Punto de inicio: [`notebooks/01_tsmom_baseline.ipynb`](notebooks/01_tsmom_baseline.ipynb), **Block 01 — Data Audit**.
- Restricción metodológica: toda señal y PnL futuros deberán respetar causalidad; no se permite *look-ahead*.

## Disponibilidad Gold al preparar el laboratorio

| Símbolo | Estado Gold | Acción reproducible si falta |
| --- | --- | --- |
| `SPY` | Disponible: `data/gold/daily_series/etf/SPY.parquet` | Ninguna. |
| `QQQ` | Disponible: `data/gold/daily_series/etf/QQQ.parquet` | Ninguna. |
| `XLE` | Disponible: `data/gold/daily_series/etf/XLE.parquet` | Ninguna. |
| `GLD` | Disponible: `data/gold/daily_series/etf/GLD.parquet` | Ninguna. |

Los cuatro instrumentos superaron la promoción Gold el `2026-11-17`. Si fuera necesaria una actualización antes de validar, ejecutar `data_ingest/run_daily_pipeline.py` desde la raíz del proyecto con `--asset-class etf` y la última sesión estadounidense completada.

El pipeline intradía no forma parte de este laboratorio.

