# Auditoría de factibilidad — IV SPY cercana a 30 días

Fecha: 2026-09-27  
Modo: lectura local. No se llamó a la API, no se descargaron datos, no se entrenaron modelos y no se calcularon resultados predictivos.

## Pregunta en alcance

> ¿La volatilidad implícita de opciones SPY cercana a 30 días informa mejor sobre la volatilidad realizada de las próximas 20 sesiones que `vol20` conocida en la fecha de observación?

Esta auditoría solo comprueba si los datos locales permiten construir una serie diaria de IV y, posteriormente, evaluarla. No construye la serie definitiva, no calcula volatilidad realizada ni compara predictores.

## Decisión

**FACTIBLE con datos locales**, para construir y evaluar históricamente una serie diaria de IV SPY cercana a 30 días: hay cadenas originales recuperables para 1,674 sesiones, con IV, tipo, strike, vencimiento y cotizaciones, y una cobertura 30D/ATM utilizable de 1,673 sesiones (99.94%).

La salvedad principal es temporal: el proveedor archivado identifica una **fecha** de cadena, pero no una hora o marca EOD verificable. Por tanto, la factibilidad de una serie histórica no prueba que la IV estuviera disponible antes de la sesión siguiente. Una marca horaria de cotización/publicación, o documentación del proveedor que fije inequívocamente esa hora, sería necesaria para verificar ese reloj.

## Inventario y procedencia

| Fuente local | Tipo | Rango real | Sesiones/filas | Contenido y procedencia |
|---|---|---|---:|---|
| `data/raw/spy_historical_options_YYYY-MM-DD.json.gz` (1,610) y `.json` (64) | Cadenas originales | 2020-01-02–2026-08-31 | 1,674 respuestas; 16,043,752 registros de contratos | Respuestas archivadas de `HISTORICAL_OPTIONS` para SPY. Son la fuente recuperable de contrato a contrato. |
| `reports/checkpoint_a4_daily.csv` | Tabla derivada | 2020-01-02–2026-08-31 | 1,674 filas, una por sesión | Par delta-25 seleccionado por A4, sus IV/bid/ask y skew; **no** contiene la cadena completa ni es apropiada como fuente única de IV ATM 30D. |
| `data/derived/spy_daily_adjusted_2020_2026.csv` | Tabla derivada de precios diarios | 2020-01-02–2026-08-31 | 1,674 filas | `open`, `high`, `low`, `close`, `adjusted_close`, volumen, dividendos y splits. Se usó `close` del mismo día únicamente para la sonda de moneyness; no aparece dentro de los registros de opciones. |
| `scripts/audit_checkpoint_a4_full_history.py` | Código de procedencia A4 | — | — | Descargaba/archivaba las respuestas originales y derivaba `checkpoint_a4_daily.csv` usando la regla delta-25. No se ejecutó en esta auditoría. |

Las 1,674 rutas de respuesta A4 tienen cadena local correspondiente; no hay una parte del calendario A4 que subsista solo como skew derivado sin respuesta recuperable. La excepción de selección A4 es 2020-06-23 (`no_eligible_put`), pero su respuesta bruta permanece archivada.

### Campos observados en la cadena original

El conjunto de campos de contrato observado es:

`contractID`, `symbol`, `expiration`, `strike`, `type`, `last`, `mark`, `bid`, `bid_size`, `ask`, `ask_size`, `volume`, `open_interest`, `date`, `implied_volatility`, `delta`, `gamma`, `theta`, `vega` y `rho`.

- IV, bid, ask, strike, vencimiento, tipo (`call`/`put`), delta, volumen y open interest son campos observados del proveedor.
- `date` es la fecha de cadena/cotización declarada por el proveedor. No existe campo de hora, zona horaria, timestamp de cotización, timestamp de publicación ni precio del subyacente dentro de los registros originales.
- DTE, moneyness, spread relativo y banderas de elegibilidad son cálculos locales. `skew`, flags de spread y los pares seleccionados en A4 también son derivados por código local.
- El precio contemporáneo de SPY no es un campo de cadena: en esta auditoría se unió el `close` diario local por fecha. Hubo precio diario local para las 1,674 sesiones; la contemporaneidad intradía/EOD entre ese cierre y la cadena no se puede verificar con el archivo.

La cadena contiene entre 0 y 18,800 registros por sesión (mediana 9,362) y entre 0 y 51 vencimientos distintos (mediana 34). El cero corresponde a la sesión sin cadena elegible indicada arriba. Se encontraron 9,282 filas de contrato duplicadas por `contractID` dentro de su sesión; cualquier construcción posterior tendrá que definir un tratamiento explícito de duplicados.

## Sonda de cobertura 30D/ATM en todas las sesiones

Para evitar presentar una regla de producción, se fijó **solo para esta auditoría** la sonda descriptiva siguiente antes de contar: contratos con 21–45 DTE calendario y `|strike / close_SPY - 1| <= 2%`, donde `close_SPY` es el cierre diario local no ajustado del mismo día. La banda no es una definición definitiva de “cercano a 30 días” ni de ATM.

Una sesión sobrevive un control si existe al menos un contrato de la sonda que lo cumple. La última columna exige simultáneamente IV finita, bid > 0 y ask >= bid; no incorpora un límite de spread.

| Año | Sesiones brutas | 21–45 DTE | 30D/ATM ±2% | IV finita | bid > 0 | ask >= bid | IV+bid+ask utilizables | 27–33 DTE y ATM ±2% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 253 | 252 | 252 | 252 | 252 | 252 | 252 | 252 |
| 2021 | 252 | 252 | 252 | 252 | 252 | 252 | 252 | 252 |
| 2022 | 251 | 251 | 251 | 251 | 251 | 251 | 251 | 251 |
| 2023 | 250 | 250 | 250 | 250 | 250 | 250 | 250 | 250 |
| 2024 | 252 | 252 | 252 | 252 | 252 | 252 | 252 | 252 |
| 2025 | 250 | 250 | 250 | 250 | 250 | 250 | 250 | 250 |
| 2026 | 166 | 166 | 166 | 166 | 166 | 166 | 166 | 166 |
| **Total** | **1,674** | **1,673** | **1,673** | **1,673** | **1,673** | **1,673** | **1,673** | **1,673** |

La sonda reunió 343,218 cotizaciones de contrato con IV finita, bid > 0 y ask >= bid. Sus spreads relativos `(ask-bid)/mid` tuvieron mediana 0.718%, percentil 95 de 8.023% y máximo 159.579%; se reportan para describir calidad, no para imponer un filtro retrospectivo.

## Ejemplos repartidos en el historial

En cada fecha se muestran los contratos de la sonda más cercanos a ATM, uno call y uno put cuando existen. Son ejemplos de campos disponibles, no una selección de serie definitiva.

| Fecha cadena | Tipo | Vencimiento (DTE) | Strike / cierre SPY | IV | Bid / ask | Spread rel. | Delta | Volumen / OI | ID |
|---|---|---|---|---:|---|---:|---:|---|---|
| 2020-01-02 | Call | 2020-01-31 (29) | 325.00 / 324.87 | 0.10268 | 3.88 / 3.91 | 0.770% | 0.51723 | 5,881 / 6,562 | `SPY200131C00325000` |
| 2020-01-02 | Put | 2020-01-31 (29) | 325.00 / 324.87 | 0.10268 | 3.51 / 3.54 | 0.851% | -0.48277 | 762 / 2,239 | `SPY200131P00325000` |
| 2021-07-01 | Call | 2021-07-30 (29) | 430.00 / 430.43 | 0.11244 | 5.57 / 5.60 | 0.537% | 0.51990 | 4,010 / 4,404 | `SPY210730C00430000` |
| 2021-07-01 | Put | 2021-07-30 (29) | 430.00 / 430.43 | 0.11244 | 5.12 / 5.14 | 0.390% | -0.48010 | 1,557 / 774 | `SPY210730P00430000` |
| 2022-10-03 | Call | 2022-11-02 (30) | 367.00 / 366.61 | 0.27829 | 11.82 / 11.87 | 0.422% | 0.52324 | 118 / 262 | `SPY221102C00367000` |
| 2022-10-03 | Put | 2022-11-02 (30) | 367.00 / 366.61 | 0.26853 | 10.85 / 10.90 | 0.460% | -0.47705 | 508 / 464 | `SPY221102P00367000` |
| 2023-12-29 | Call | 2024-01-26 (28) | 475.00 / 475.31 | 0.10268 | 6.77 / 6.80 | 0.442% | 0.57179 | 3,696 / 4,133 | `SPY240126C00475000` |
| 2023-12-29 | Put | 2024-01-26 (28) | 475.00 / 475.31 | 0.11244 | 4.60 / 4.63 | 0.650% | -0.43336 | 2,027 / 2,575 | `SPY240126P00475000` |
| 2025-04-03 | Call | 2025-05-02 (29) | 537.00 / 536.70 | 0.26853 | 16.88 / 16.95 | 0.414% | 0.53026 | 48 / 3 | `SPY250502C00537000` |
| 2025-04-03 | Put | 2025-05-02 (29) | 537.00 / 536.70 | 0.24902 | 14.46 / 14.57 | 0.758% | -0.46965 | 55 / 137 | `SPY250502P00537000` |
| 2026-08-31 | Call | 2026-09-30 (30) | 767.00 / 767.05 | 0.11244 | 10.82 / 10.87 | 0.461% | 0.54407 | 932 / 332 | `SPY260930C00767000` |
| 2026-08-31 | Put | 2026-09-30 (30) | 767.00 / 767.05 | 0.13195 | 10.03 / 10.08 | 0.497% | -0.46037 | 789 / 657 | `SPY260930P00767000` |

## Límite de disponibilidad temporal

El código A4 solicita `HISTORICAL_OPTIONS` por fecha y archiva la respuesta (`scripts/audit_checkpoint_a4_full_history.py`). La respuesta preservada contiene `date`, pero ninguna hora de cotización o de publicación. Por ello:

- se puede alinear una IV a una fecha de sesión histórica;
- **no se puede afirmar con los archivos actuales** que la cadena fue conocida antes de abrir `t+1`, ni que coincide exactamente con el cierre usado como precio SPY;
- este límite no impide construir la serie histórica, pero sí obliga a tratar cualquier uso operativo o prospectivo como condicional a un supuesto EOD no verificado.

No se diseñó modelo, no se eligió construcción final de IV (call, put, promedio, interpolación o superficie), y no se comparó IV contra `vol20`.
