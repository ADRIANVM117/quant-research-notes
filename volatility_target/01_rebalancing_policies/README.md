
## Sesión 03 — Del modelo a una política operativa

La pregunta que investigaremos será:

> ¿Puede una política de rebalanceo con bandas de tolerancia reducir los costos de implementación del volatility targeting sin deteriorar significativamente el control del riesgo?

### ¿Qué vamos a comparar?

Utilizaremos SPY con datos históricos de Alpha Vantage.

Mantendremos fijo inicialmente:

- Estimador: EWMA con \\(\lambda=0.94\\).
- Volatilidad objetivo: 12% anualizada.
- Apalancamiento máximo: 1×.
- Decisiones basadas únicamente en información disponible.
- Capital inicial: $200,000 MXN, aunque expresaremos los resultados principalmente en porcentajes para separar rendimiento de capital.

Compararemos tres políticas:

| Política         | Regla                                                                  |
| ---------------- | ---------------------------------------------------------------------- |
| P0 — Daily       | Rebalancear diariamente al peso objetivo                               |
| P1 — Banda 5 pp  | Rebalancear si el peso efectivo se desvía más de 5 puntos porcentuales |
| P2 — Banda 10 pp | Rebalancear si la desviación supera 10 puntos porcentuales             |

Las bandas son hipótesis de investigación, no parámetros que ya consideremos óptimos.

### ¿Qué mediremos?

Dos dimensiones separadas.

Calidad del control del riesgo:

- Volatilidad realizada del portafolio.
- Error respecto al objetivo del 12%.
- Máximo drawdown.

Utilidad económica:

- CAGR neto.
- Turnover anual.
- Costos de transacción.
- Crecimiento geométrico.

Además, utilizaremos un benchmark de exposición constante comparable para no atribuir automáticamente las mejoras a la política dinámica.

### Una decisión metodológica importante

La exposición efectiva cambia con los movimientos del mercado incluso cuando no realizamos operaciones.

Por tanto, una banda debe comparar el peso objetivo contra el peso efectivo actualizado, no simplemente contra el peso asignado en el último rebalanceo.

Por ejemplo, si inicialmente asignamos 60% a SPY y posteriormente SPY sube, su peso dentro del portafolio aumentará aunque no hayamos enviado ninguna orden.

Eso importa para reproducir correctamente una política implementable.

## Primer paso práctico: definir el experimento

Antes de programar, necesitamos fijar una sola cuestión: cuándo se calcula la señal y cuándo se ejecuta la orden.

Mi propuesta inicial:

1. Al cierre de \\(t\\), observamos el rendimiento de SPY y actualizamos EWMA.
2. Calculamos el peso objetivo para la siguiente sesión.
3. Ejecutamos el rebalanceo en la apertura de \\(t+1\\).
4. Evaluamos el rendimiento posterior a la ejecución, incluyendo costos.

Esta convención evita utilizar el cierre de \\(t\\) para operar retroactivamente a ese mismo precio.

También introduce el riesgo real de movimientos entre el cierre y la apertura.

