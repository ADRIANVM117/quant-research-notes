# Straddle ATM SPY y movimiento terminal

**Estado: CERRADO.** La evaluación descrita abajo es la única evaluación exploratoria del proyecto. No se añadieron comparadores, variantes, filtros ni experimentos posteriores.

## Pregunta e hipótesis económica

**Pregunta.** ¿El costo relativo de un straddle ATM de SPY anticipa el movimiento absoluto de SPY hasta su vencimiento mejor que una estimación basada solo en retornos históricos?

**Hipótesis.** El precio conjunto de una call y una put del mismo strike y vencimiento puede contener información sobre la magnitud del movimiento futuro que no está completa en los retornos pasados. Tanto el costo del par como el movimiento terminal se expresan respecto al precio SPY conocido en la fecha de observación.

## Definiciones evaluadas

- **Predictor straddle:** para el par call–put del mismo strike y vencimiento ya seleccionado, con 27–33 DTE, cotizaciones válidas y spread relativo de cada lado ≤10%, `straddle_mid_rel_t = (call_mid + put_mid) / SPY_close_t`. No es volatilidad implícita.
- **Benchmark histórico:** `historical_move_baseline_t` es el promedio de las últimas 252 ventanas históricas completas de horizonte `H`, donde `H` es el número de sesiones entre `t` y el vencimiento `T`; cada ventana es `abs(SPY_close_u / SPY_close_(u-H) - K / SPY_close_t)` y termina en `u ≤ t`.
- **Movimiento terminal:** `terminal_move_rel = abs(SPY_close_T - K) / SPY_close_t`, con cierre sin ajustar observado exactamente en `T`. Es el valor intrínseco conjunto relativo al vencimiento, no P&L realizado.

## Separación y resultado exploratorio

El desarrollo usó 715 observaciones con resultado conocido y `T ≤ 2023-12-29`. Los coeficientes de dos regresiones lineales simples con intercepto se congelaron allí; cualquier predicción negativa se truncó a cero para ambos modelos.

La evaluación histórica común contiene 648 fechas de `t` entre 2024-01-02 y 2026-08-03, con vencimientos observados hasta 2026-08-31:

| Predictor calibrado | MSE | RMSE | MAE |
|---|---:|---:|---:|
| Benchmark histórico | 0.00071901 | 0.02681443 | 0.02148072 |
| Straddle | 0.00051880 | 0.02277725 | 0.01808196 |

La diferencia `MSE_baseline - MSE_straddle` fue 0.00020021: una reducción de MSE de **27.8%** frente a este benchmark. El IC exploratorio de 95% por bootstrap de bloques de 30 fechas (5,000 réplicas; semilla 20260927) fue **[0.00011880, 0.00033096]**.

## Auditoría del benchmark

La pendiente OLS de desarrollo del benchmark fue −0.15284988. La auditoría independiente de sus 715 filas verificó el linaje contra el CSV terminal original, `H`, `K / SPY_close_t`, las 252 ventanas, sus fechas, el límite de cierres `≤ t`, los splits y los promedios. No encontró un error de construcción. La pendiente negativa queda como relación empírica descriptiva de esa muestra bajo la definición congelada; no justifica cambiar el benchmark después de verla.

## Alcance de la conclusión

El resultado favorece al predictor straddle **frente a este benchmark histórico** en una evaluación histórica exploratoria. No demuestra superioridad frente a cualquier método histórico, rentabilidad de comprar opciones ni validez prospectiva. El periodo 2024–2026 ya había sido visto y no es una prueba prospectiva intacta.

Persisten límites materiales:

- la disponibilidad EOD de la cadena antes de una decisión posterior es un supuesto no verificado;
- SPY tiene opciones americanas;
- bid y ask archivados no demuestran ejecución simultánea de call y put;
- por ello, prima y valor intrínseco no se interpretan como P&L de una operación real.

## Formulación breve para CV

> Diseñé una investigación reproducible con cadenas históricas de opciones SPY: construí un predictor descriptivo de costo relativo de straddle ATM, lo comparé con un benchmark de movimiento histórico en una separación temporal congelada y audité el linaje de datos, el no-look-ahead y las limitaciones de ejecución. El resultado exploratorio favoreció al straddle frente al benchmark especificado, sin presentarlo como evidencia de rentabilidad ni validación prospectiva.

## Artefactos principales

- `docs/straddle_terminal_move_exploratory_protocol_2026-09-27.md`: protocolo congelado.
- `reports/straddle_terminal_move_exploratory_evaluation.md`: resultado exploratorio.
- `reports/historical_baseline_negative_slope_audit.md`: auditoría de la pendiente negativa.
- `notebooks/06_straddle_terminal_move_exploratory_evaluation.ipynb`: evaluación visible.
- `notebooks/07_historical_baseline_negative_slope_audit.ipynb`: auditoría visible.
