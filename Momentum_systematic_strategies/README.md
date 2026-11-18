# Momentum Systematic Strategies

Proyecto de investigación para diseñar, auditar y evaluar estrategias sistemáticas de momentum. La infraestructura común preserva datos diarios reproducibles; cada línea de investigación vive de forma independiente y consume únicamente series Gold validadas.

## Arquitectura y flujo de datos

```text
Alpha Vantage -> data_ingest/ -> data/parquet/ (Silver)
                              -> data_quality/ -> data/gold/daily_series/<asset_class>/ (Gold)
                                                           -> <research_line>/notebooks/
```

- **Fuente inicial:** Alpha Vantage (`TIME_SERIES_DAILY_ADJUSTED`).
- **Frecuencia inicial:** diaria.
- **Fuente canónica para investigación:** `data/gold/daily_series/<asset_class>/`.
- **Ruta que usarán los notebooks TSMOM:** `data/gold/daily_series/etf/<SYMBOL>.parquet`.

Las series crudas, Silver, Gold y los reportes de calidad son locales e ignorados por Git. Los notebooks no deben leer `data/raw/`, `data/parquet/` ni `series/`.

## Investigación

| Línea | Estado |
| --- | --- |
| `01_tsmom` | Preparada para iniciar el laboratorio base diario. |
| `02_factor_momentum` | Planeada; no implementada. |
| `03_regime_aware_momentum` | Planeada; no implementada. |
| `04_deep_momentum_networks` | Planeada; no implementada. |
| `05_momentum_transformer` | Planeada; no implementada. |

El primer laboratorio está congelado en el universo ETF `SPY`, `QQQ`, `XLE` y `GLD`, y comienza con **Block 01 — Data Audit**. No hay todavía señales, construcción de cartera, backtests, métricas ni resultados de momentum.

## Pipeline diario

La ingesta deja la respuesta inmutable en `data/raw/`, normaliza la historia en Silver (`data/parquet/<asset_class>/`) y el control de calidad promueve series aprobadas a Gold.

Para actualizar una serie diaria y ejecutar su puerta de calidad, usa la fecha de la última sesión estadounidense completada:

```powershell
python data_ingest/run_daily_pipeline.py --symbol SPY --asset-class etf --expected-session-date YYYY-MM-DD
```

Para validar una serie Silver existente y promoverla a Gold sin descargar:

```powershell
python data_quality/validate_daily_sanity.py --asset-class etf --symbol QQQ
```

El universo TSMOM sólo tiene SPY disponible actualmente en Gold. `QQQ`, `XLE` y `GLD` existen en Silver pero aún no en Gold: ejecutar el comando de validación anterior, sustituyendo el símbolo, es el paso reproducible requerido para producir sus copias Gold. Si una serie Silver deja de estar disponible o necesita actualizarse, usar primero `run_daily_pipeline.py` y luego la validación.

El pipeline intradía permanece fuera de alcance: `01_tsmom` usa exclusivamente datos diarios.

## Entorno y deuda técnica

`.venv/` es un entorno heredado y se conserva por ahora; deberá recrearse posteriormente desde `requirements.txt`. En la auditoría inicial, `plotly==6.2.0` estaba declarado pero ausente de ese entorno heredado.

La prueba interna de calidad (`--self-test`) tiene una deuda técnica bajo OneDrive: no puede crear o limpiar temporales en `data/.tmp/`. No bloquea la organización de esta estructura y no se modifica en esta etapa.

## Política para `series/`

`series/SPY.parquet` se conserva localmente y no se elimina de forma destructiva. Fue verificado como una copia byte a byte idéntica de `data/gold/daily_series/etf/SPY.parquet` (SHA-256 `567C7F241A39E2EE2CC7FC8872404350A331AC1C41F4C2BD70FCBDB36F0AC967`). `series/` está ignorado por Git para evitar que se convierta en una fuente paralela; toda investigación debe leer Gold.

