# Inventario de datos y procedencia

Este proyecto referencia datos ya archivados en el proyecto independiente `HMM_regime_options`; no duplica las cadenas de opciones.

| Recurso | Ruta relativa desde este proyecto | Procedencia / uso permitido en esta fase |
|---|---|---|
| Cadenas originales SPY | `../../HMM_regime_options/data/raw/spy_historical_options_YYYY-MM-DD.json.gz` y `.json` | Respuestas históricas archivadas de `HISTORICAL_OPTIONS`; fuente contrato a contrato. Rango auditado: 2020-01-02–2026-08-31. |
| Tabla de precios diarios SPY | `../../HMM_regime_options/data/derived/spy_daily_adjusted_2020_2026.csv` | Precios diarios locales para alinear fechas y moneyness; no es parte de una cadena de opciones. |
| Tabla A4 derivada | `../../HMM_regime_options/reports/checkpoint_a4_daily.csv` | Pares delta-25 y skew derivados; no sustituye las cadenas originales para construir IV cercana a 30 días. |
| Auditoría copiada | `options_iv30_data_feasibility_audit.md` | Copia de referencia del informe de factibilidad, conservando su original en `HMM_regime_options/docs/`. |
| Código de procedencia A4 | `../../HMM_regime_options/scripts/audit_checkpoint_a4_full_history.py` | Código que archivó cadenas y produjo tablas A4; no se ejecuta desde este proyecto durante esta preparación. |

## Restricción de datos

No se copiarán los aproximadamente 16 millones de contratos al proyecto. Toda lectura futura deberá declarar que usa estas rutas compartidas y preservar los archivos originales.

## Límite de reloj

Las respuestas de opciones contienen fecha, pero no una hora de cotización/publicación verificable. La disponibilidad para una decisión en `t+1` permanece como supuesto EOD no verificado.
