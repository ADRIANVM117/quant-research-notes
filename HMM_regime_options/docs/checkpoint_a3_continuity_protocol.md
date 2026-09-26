# Checkpoint A3 — continuidad diaria v1

Fecha de registro: 2026-09-25  
Estado: fijado antes de consultas de cadenas para esta variante. No modifica
los protocolos ni reportes A, A2/v2 anteriores.

## Muestra calendario preespecificada

Se usan los tres meses completos siguientes, todos enero y en años distintos:

| Mes | Sesiones esperadas | Motivo de elección |
|---|---:|---|
| 2025-01 | 20 | Año reciente con cobertura disponible en la serie diaria ya archivada. |
| 2023-01 | 20 | Punto intermedio temporal, mismo mes calendario para evitar estacionalidad de mes. |
| 2021-01 | 19 | Punto anterior, mismo mes calendario, para comprobar continuidad temporal. |

La lista de sesiones esperadas se congela desde las fechas existentes en la
respuesta diaria de SPY ya guardada, no desde la disponibilidad o resultado de
las cadenas. En particular, 2025-01-09 no aparece como sesión en esa serie.

## Selección por par

Se aplica sin cambios `checkpoint_a_pair_selection_v2.md`: mismo vencimiento;
21–45 DTE; puts con delta [-0.35, -0.15] y calls [+0.15, +0.35]. Se escoge el
par mediante la tupla: distancia a 30 DTE, suma de errores absolutos de delta,
mayor error individual, ID put e ID call. No se ajusta por fecha ni por
cotizaciones.

## Cotizaciones y continuidad

Se conserva `wide_spread` si `(ask-bid)/mid > 0.20` con bid/ask positivos,
válidos y ask >= bid. Una cotización de par es **utilizable** si ambos contratos
tienen bid y ask numéricos y finitos, bid > 0 y ask >= bid. El spread amplio se
marca aparte y no altera la selección ni esta condición básica de utilización.

`bid_zero`, `ask_below_bid` y `missing_or_invalid_bid_ask` se mantienen como
problemas separados. El hueco consecutivo mide sesiones esperadas sucesivas
sin un par de cotizaciones utilizables, incluidos fallos de API, ausencia de
par o problema de cotización.

El skew diario es `IV_put - IV_call` del par elegido. Antes de ver resultados,
un salto se marca cuando el cambio absoluto respecto al skew disponible previo
supera 0.05 (cinco puntos de IV); se señala por separado si coincide con un
cambio de vencimiento. Es una bandera descriptiva, no causal.

La fecha de cadena se registra. Como no hay timestamp EOD histórico verificable
del proveedor, la señal de fecha t se mantiene como disponible solo para la
siguiente sesión de mercado.

## Criterio para ampliar la auditoría temporal

- **GO:** respuestas y pares elegibles para al menos 95% de sesiones esperadas
  en cada mes, sin huecos de cotización utilizable mayores de una sesión.
- **REVISAR:** cobertura suficiente pero cualquier mes incumple una de esas
  condiciones, o persisten fallos de API/cotización que requieren diagnóstico.
- **STOP:** no puede obtenerse una cobertura material de cadenas comparables.

La decisión concierne exclusivamente a factibilidad de datos para varios años;
no evalúa alerta, predicción ni HMM.
