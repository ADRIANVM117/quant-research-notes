# XLE Systematic Momentum 126d

## Hipótesis económica

La hipótesis es que, para XLE, el momentum de la componente atribuida a mercado, size y growth/value puede distinguir periodos de exposición más favorables que el momentum total del propio ETF. Es una hipótesis exploratoria: XLE fue seleccionado después de observar resultados históricos.

## Señal congelada

- Activo: XLE.
- Formación: 126 sesiones.
- Atribución: OLS rolling de 252 sesiones con intercepto.
- Proxies: `MKT = SPY`, `SIZE = IWM - SPY`, `GV = IWF - IWD`.
- Decisión: long si el momentum sistemático acumulado es positivo; cash en caso contrario.
- Sin apalancamiento, cortos ni cambios de umbral.
- La señal se conoce al cierre de `t`; la orden se prepara entonces para una simulación de fill en la apertura de `t+1`.

La candidata se compara con Buy & Hold, TSMOM total de 126 sesiones y Market Momentum de SPY de 126 sesiones.

## Resultados históricos exploratorios

La notebook de señal encontró, en la ventana investigada, un mejor perfil histórico para XLE Systematic Momentum que para TSMOM total. Ese resultado motivó esta evaluación operativa; no constituye una validación independiente ni alpha confirmado.

## Ejecución y fricciones

`notebooks/01_execution_feasibility.ipynb` reconstruye las señales y verifica su coincidencia con la notebook de origen en fechas comunes. Simula capital inicial de USD 10,000, acciones enteras, cash no negativo y fills en la apertura siguiente.

La comisión documentada usa el esquema **IBKR Pro Fixed** para acciones/ETFs estadounidenses: USD 0.005 por acción, mínimo USD 1 por orden y máximo 1% del valor negociado. Fuente consultada el 2026-11-19: [Interactive Brokers — Commissions Stocks](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php). No se modelan comisiones regulatorias adicionales, exchange fees, impuestos ni spreads observados.

El escenario con slippage añade 5 bps adversos por fill como supuesto ilustrativo; no es un spread histórico ni una tarifa de IBKR.

## Limitaciones

- Las señales y los resultados proceden del mismo historial usado para seleccionar XLE.
- Los OHLC diarios no contienen bid/ask, profundidad, prioridad de cola ni fills reales.
- Los dividendos de Gold se acreditan como efectivo en la fecha indicada por la serie; eso aproxima el efecto económico, no el calendario real de pago.
- Los splits se aplican al número de acciones antes de la apertura de su fecha registrada. Cualquier diferencia de convención del proveedor limita la fidelidad contable.
- La simulación no representa PnL real de IBKR ni una conexión operativa.

## Objetivo futuro

Si la viabilidad persiste después de estas fricciones, la siguiente etapa será observación prospectiva en paper trading con esta especificación congelada y datos que no participaron en la selección de XLE.
