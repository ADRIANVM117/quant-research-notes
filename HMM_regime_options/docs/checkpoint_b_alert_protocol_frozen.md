# Checkpoint B — protocolo de alerta congelado v1

Fecha de congelamiento: 2026-09-26  
Estado: congelado antes de calcular resultados. V2 se conserva sin cambios.

## Alcance

La prueba evalúa solo alerta de caída de SPY de 5% en diez sesiones. No evalúa otros activos, horizontes, regímenes ni HMM. Un negativo no descarta todos los HMM. Checkpoint C, cartera, costos y Actinver quedan fuera de alcance. Toda conclusión histórica es condicional al supuesto de disponibilidad siguiente.

## Datos y reloj

El campo congelado es `5. adjusted close` de Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED`, dentro de `Time Series (Daily)`, para SPY diario, zona `US/Eastern`; se denomina `A`. La respuesta archivada `TIME_SERIES_DAILY` contiene `4. close` sin ajustar y no es sustituto. Antes de ejecutar B se debe obtener, archivar y validar `TIME_SERIES_DAILY_ADJUSTED`; es un prerrequisito de datos, no cálculo.

Para score de cadena fechada `t`, se supone sin verificar que puede usarse antes de abrir `d=t+1`. No es hora demostrada ni necesariamente conservadora. El precio de referencia es `A_d`, cierre ajustado posterior a ese supuesto uso. El resultado usa `A_{d+1}...A_{d+10}`.

## Etiqueta y episodios

```text
etiqueta_d = 1 si min(A_{d+1}, …, A_{d+10}) / A_d - 1 <= -0.05
```

`brecha_d` es la primera sesión en `d+1...d+10` con `A <= 0.95*A_d`. Las brechas se agrupan recursivamente si la siguiente está a no más de cinco sesiones de la última del grupo. Cada grupo es episodio; inicio y fin son primera y última brecha. Su ventana de anticipación es `inicio-5...inicio-1`.

## Acierto, falsa alarma y asignación

Una alerta en `d` es acierto solo si un episodio inicia en `d+1...d+5`; es falsa alarma si ninguno inicia allí. Alerta más de cinco sesiones antes, en inicio o después no acredita el episodio y es falsa alarma si no acredita otro. Cada alerta se asigna como máximo al **primer** episodio cronológico cuyo inicio caiga en `d+1...d+5`. Recall cuenta episodio con alguna alerta asignada; precisión y falsas alarmas cuentan cada alerta una vez.

## Particiones

Desarrollo: 2020-01-02–2023-12-29. Validación: 2024-01-02–2024-12-31. Final: 2025-01-02–2026-08-31. La partición se asigna por `d`. Etiquetas pueden cruzar año con horizonte completo; episodios que cruzan frontera se excluyen de métricas y se reportan. Alertas no se asignan fuera de su partición. Las últimas diez decisiones sin horizonte no reciben etiqueta.

## Scores, cobertura y fechas comunes

Se mantienen `vol20 > P80_desarrollo(vol20)` y `z_skew252 >= 1.5`. `vol20` usa retornos log de 20 sesiones hasta `t`; `z_skew252` usa media/desviación de 252 sesiones hasta `t`.

El universo de cobertura es toda fecha `d` con `vol20` disponible y horizonte completo, antes de exigir skew. El denominador de cobertura de skew es ese universo completo e incluye toda fecha perdida por falta de skew. Se reportan universo total, skew disponible, falta por ausencia/calidad y falta por historia insuficiente.

La comparación primaria usa fechas comunes: ambos scores disponibles, mismo horizonte y partición. En desarrollo se congelan percentiles 90 de ambos scores sobre fechas comunes, presupuesto de alertas 10%. Empates se incluyen (`score >= percentil`); se reporta frecuencia efectiva y no se recalibra validación/final. Los umbrales originales se muestran, pero no deciden lo primario.

## Faltantes y episodios evaluables

Sin respuesta, par o cotización utilizable no hay skew ni alerta; no se imputa. `wide_spread`, salto extremo y cambio de vencimiento quedan en primario con bandera; sensibilidades son separadas. `bid_zero`, `ask_below_bid` o cotización inválida impiden alerta. IV repetida se conserva.

Un episodio con alguna fecha sin skew en sus cinco decisiones previas sigue siendo evaluable. Esa fecha equivale a ausencia de alerta. Se reportan ventanas incompletas y fechas sin skew dentro de ellas por episodio y partición.

## Métrica y decisión

La métrica primaria es recall de episodios a igual frecuencia y fechas comunes: episodios evaluables con alerta asignada / episodios evaluables. Secundarias: cobertura con el denominador anterior, frecuencia, falsas alarmas, precisión, anticipación, tasa base, cruces y sensibilidades.

**CANDIDATO** exige ventaja skew–benchmark `>=0.10` en validación/final, al menos 10 episodios finales, cobertura skew `>=95%` sobre el universo completo final y falsas alarmas skew no más de `0.02` sobre benchmark final.

**INCONCLUSO** aplica con menos de 10 episodios evaluables finales, sin importar secundarias; no es STOP ni CANDIDATO. Con 10 o más, fallo de CANDIDATO puede ser AISLADO o STOP.

## Verificación de implementabilidad

Métricas, denominadores, asignación, empates, episodios, fronteras y estados tienen reglas explícitas; no quedan decisiones pendientes sobre métricas. El único prerrequisito es archivar y validar `5. adjusted close`, que es disponibilidad de datos, no decisión metodológica. No se calcularán resultados en esta tarea.
