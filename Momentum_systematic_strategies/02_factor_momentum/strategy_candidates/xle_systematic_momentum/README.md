# XLE Systematic Momentum 126d

## Hipótesis económica

Esta candidata investiga si el momentum de la componente sistemática atribuida por un modelo factorial permite identificar periodos históricos de exposición long/cash en XLE. XLE fue seleccionada retrospectivamente después de analizar varios activos; los resultados descritos aquí son exploratorios y no constituyen validación prospectiva independiente.

## Especificación congelada

- **Activo:** XLE.
- **Factores:** $MKT = SPY$, $SIZE = IWM - SPY$ y $GV = IWF - IWD$.
- **Atribución:** rolling OLS de 252 sesiones con intercepto.
- **Momentum:** acumulación de 126 sesiones de retornos sistemáticos atribuidos.
- **Posición:** long cuando ese momentum acumulado es positivo; cash en caso contrario.
- **Restricciones:** sin posiciones cortas ni apalancamiento.
- **Cronología:** la señal se conoce al cierre de $t$ y el fill se simula en la apertura de $t+1$.

El retorno sistemático atribuido incluye el intercepto rolling y no sólo las contribuciones de los ETFs factoriales. La candidata se compara con Buy & Hold, TSMOM total de 126 sesiones y Market Momentum de SPY de 126 sesiones, sin cambiar umbrales ni horizontes para mejorar los resultados.

## Ejecución y contabilidad modeladas

La simulación comienza con USD 10,000, usa acciones enteras y exige efectivo no negativo durante 1,853 sesiones de ejecución. Las órdenes se preparan con información disponible tras el cierre y se ejecutan de forma simulada en la apertura siguiente.

El escenario central aplica **IBKR Pro Fixed modelado** —USD 0.005 por acción, mínimo USD 1 por orden y máximo 1% del valor negociado— junto con 5 bps de slippage adverso por fill. Los dividendos de Gold se acreditan como efectivo y los splits ajustan el número de acciones según el campo registrado en Gold.

Los precios ajustados se emplean para construir la señal; los fills usan OHLC. No se modelan bid/ask, profundidad, prioridad de cola, impacto de mercado, fills reales, tarifas regulatorias ni costes observados de IBKR. El efecto económico de `adjusted_close` y los dividendos acreditados como efectivo siguen convenciones distintas y no deben tratarse como equivalentes.

## Resultados económicos históricos

Escenario: **IBKR Pro Fixed modelado + 5 bps de slippage adverso**.

| Métrica | Systematic | Buy & Hold |
| --- | ---: | ---: |
| Capital final | USD 28,028.02 | USD 23,494.51 |
| CAGR | 15.046% | 12.318% |
| Max drawdown | −27.805% | −57.981% |

Systematic realizó 63 operaciones históricas. Su Sharpe simulado fue 0.618. Estas cifras no sustituyen un PnL real de IBKR ni establecen alpha confirmado.

## Sensibilidad económica

| Slippage | CAGR de Systematic |
| --- | ---: |
| 0 bps | 15.536% |
| 5 bps | 15.046% |
| 10 bps | 14.583% |
| 20 bps | 13.590% |

Retrasar una sesión la ejecución redujo el CAGR a 13.195%, frente al 15.046% programado. La comparación usa 1,852 sesiones en el caso retrasado y 1,853 en el programado, por lo que es una sensibilidad de calendario y no un experimento perfectamente equivalente.

El bootstrap por bloques utiliza retornos idealizados sin costes de la notebook de señales. Describe la sensibilidad histórica de esa serie, pero no corrige la selección retrospectiva de XLE ni convierte probabilidades de réplicas positivas en probabilidades prospectivas de generar alpha.

## Notebooks y reproducción

La candidata forma parte de [02 — Factor Momentum](../../README.md).

- [01 — Viabilidad de ejecución](notebooks/01_execution_feasibility.ipynb) · [Abrir en Google Colab](https://colab.research.google.com/github/ADRIANVM117/quant-research-notes/blob/factor-momentum-colab-v1.1/Momentum_systematic_strategies/02_factor_momentum/strategy_candidates/xle_systematic_momentum/notebooks/01_execution_feasibility.ipynb)
- [02 — Revisión previa a paper trading](notebooks/02_pre_paper_review.ipynb) · [Abrir en Google Colab](https://colab.research.google.com/github/ADRIANVM117/quant-research-notes/blob/factor-momentum-colab-v1.1/Momentum_systematic_strategies/02_factor_momentum/strategy_candidates/xle_systematic_momentum/notebooks/02_pre_paper_review.ipynb)

Ambas notebooks se reprodujeron en Google Colab real mediante **Run all**, sin ejecutar previamente las demás notebooks. Sus bootstraps descargan los insumos públicos fijados y verifican sus hashes antes de ejecutar los cálculos.

## Limitaciones

- XLE fue seleccionada retrospectivamente; no existe validación prospectiva independiente.
- Fills, slippage y comisiones son supuestos modelados, no observaciones de IBKR.
- Los dividendos acreditados como efectivo y `adjusted_close` no representan la misma convención contable.
- Las condiciones históricas, incluidas liquidez y costes efectivos, pueden no repetirse.
- El bootstrap no confirma alpha.
- No existe PnL real de IBKR ni una estrategia validada para producción.
