# Auditoría inicial — Momentum Systematic Strategies

Fecha de auditoría: 2026-11-17.

## Dictamen

La carpeta contiene una base de **ingesta y control de calidad de precios**, copiada íntegramente de `volatility_target`; todavía no contiene investigación, señales, backtests ni documentación propios de una estrategia de momentum. Está preparada para actualizar series diarias de *equities* y ETFs mediante Alpha Vantage, pero no está lista aún para reproducir una estrategia de momentum de extremo a extremo.

## Inventario actual

- `data_ingest/`
  - `alpha_vantage_daily.py`: descarga `TIME_SERIES_DAILY_ADJUSTED`, conserva el JSON crudo y normaliza a Parquet.
  - `alpha_vantage_daily_batch.py`: actualización por lote a partir de un universo, con límite de peticiones y modo `--dry-run`.
  - `run_daily_pipeline.py`: actualización de un símbolo y validación/promoción posterior.
  - `alpha_vantage_intraday.py`: adquisición intradía independiente.
  - `daily_universe.csv`: 202 instrumentos de referencia: 107 equities para incluir (96 candidatos, 4 confirmados, 3 ADR), 43 equities en revisión/exclusión y 52 ETFs confirmados; además 4 ETFs pendientes de revisión.
- `data_quality/validate_daily_sanity.py`: valida series diarias `equity` y `etf`, genera reportes y promociona Silver a Gold. Comprueba datos, huecos contra un calendario de consenso provisional y acciones corporativas.
- `data/` (ignorado por Git): 318 MB.
  - 218 respuestas crudas (279 MB).
  - 103 series diarias de equities, con cobertura agregada 2018-01-02 a 2026-10-20.
  - 53 series diarias de ETFs, con cobertura agregada 2018-01-02 a 2026-11-10.
  - 10 Parquet intradía, 22 históricos intradía y material experimental de 5 minutos.
  - Un Gold aprobado: `etf/SPY.parquet`; tres reportes de calidad.
- `series/SPY.parquet`: una copia de 2,227 sesiones, 2018-01-02 a 2026-11-10, con OHLC, cierre ajustado, volumen, dividendos, *splits* y metadatos de proveedor.
- Configuración: `.env` con claves de Alpha Vantage y SEC Edgar, correctamente ignorado. `.gitignore` también excluye `.venv`, raw, Parquet, Gold, calidad y temporales.
- Dependencias declaradas: `polars`, `requests`, `python-dotenv`, `tzdata` y `plotly`.

## Verificaciones realizadas

- Los cinco scripts Python pasan compilación estática.
- Las interfaces de descarga diaria individual, lote e intradía funcionan al consultar `--help`.
- Todo el código, catálogo, dependencias, `.gitignore` y README es idéntico a `volatility_target`.
- La carpeta completa aún no está versionada (`git status` la reporta como no rastreada). Los datos bajo `data/` sí quedarán excluidos al añadirla, pero `series/SPY.parquet` **no** está ignorado y se añadiría al repositorio.

## Hallazgos y acciones recomendadas

1. **Prioridad alta — reemplazar `README.md`.** Dice “Volatility target” y describe una plantilla portable. Debe presentar el objetivo de momentum, universo, frecuencia, fuente, secuencia reproducible y estado de cada investigación. No conviene borrarlo sin sustituirlo: mantener las instrucciones de ingesta como una sección o moverlas a `docs/data_pipeline.md`.
2. **Prioridad alta — definir el núcleo de investigación.** Faltan especificación de señal (cross-sectional, time-series o ambas), retornos usados, formación/holding, *rebalance*, costes, *volatility scaling*, benchmark y tests de sesgos. Tampoco hay notebooks/scripts de señales, cartera, backtest, métricas o resultados.
3. **Prioridad alta — decidir la política de datos para `series/`.** Añadir `series/` a `.gitignore` si es una salida/copia local; si SPY es un pequeño *fixture* de prueba, moverlo explícitamente a `tests/fixtures/` y documentar su procedencia. Evitar añadirlo por accidente.
4. **Prioridad alta — recrear el entorno.** La `.venv` copiada pesa ~409 MB y no debe viajar con el proyecto. El entorno actual no tiene `plotly==6.2.0`, aunque `requirements.txt` lo declara; por tanto no satisface completamente el manifiesto. Crear una `.venv` nueva desde `requirements.txt` y eliminar la copia sólo cuando no esté bloqueada por OneDrive.
5. **Prioridad media — reparar la prueba de calidad en OneDrive.** `validate_daily_sanity.py --self-test` no pudo crear/eliminar Parquet en `data/.tmp` por `PermissionError`. Debe usar el directorio temporal del sistema o un directorio escribible fuera de OneDrive. El intento dejó `data/.tmp/tmp5_7hod8z`, ignorado por Git, que no pudo eliminarse por el mismo bloqueo.
6. **Prioridad media — separar el legado intradía.** Hay scripts, logs, CSV/Parquet y archivos de adquisición de 1 y 5 minutos dentro de una estructura ignorada, pero no se documentan ni pasan por la puerta de calidad diaria/Gold. Decidir si formarán parte del alcance momentum; de no ser así, archivarlos fuera del proyecto nuevo.
7. **Prioridad media — limitar afirmaciones de calidad.** El calendario de sesiones es explícitamente provisional y sólo cubre `equity`/`etf`. No está listo para bonos, futuros, FX, cripto, índices o mercados no estadounidenses sin adaptar calendario, esquema, proveedor y reglas de calidad.
8. **Prioridad media — endurecer la identidad del universo.** 96 equities están marcadas como `CANDIDATE`, tres son ADR proxy y 43 están en revisión/exclusión. No usar ese conjunto como universo definitivo de investigación sin cerrar identidad, moneda, mercado y posible sesgo de supervivencia.

## Estado de preparación

| Capacidad | Estado |
| --- | --- |
| Descargar/actualizar daily equity y ETF de Alpha Vantage | Sí, con configuración privada y atención a cuotas. |
| Descargar una nueva clase de activo | No; el código y validador sólo aceptan `equity` y `etf`. |
| Ejecutar control de calidad diario y promover a Gold | Parcial; lógica disponible, prueba local bloqueada por `data/.tmp` en OneDrive. |
| Reproducir precios diarios existentes | Parcial; raw y Parquet locales están ignorados y no se reconstruyen al clonar sin API key/descarga. |
| Reproducir una estrategia momentum | No; aún faltan especificación, implementación, dependencias de investigación y resultados. |

