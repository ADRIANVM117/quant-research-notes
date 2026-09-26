# Checkpoint B — protocolo de alerta v2 propuesto

Fecha: 2026-09-26  
Estado: propuesta para aprobación; v1 se conserva sin cambios. No se calculan etiquetas, métricas, asociaciones, desempeño ni HMM.

## Alcance

Esta prueba evalúa exclusivamente una alerta de **caída de SPY de 5% en diez sesiones**. Un resultado negativo no descarta otros horizontes, activos, definiciones de régimen ni todos los posibles HMM. No prueba causalidad del skew ni utilidad de cartera.

## Reloj y etiqueta

El score de una cadena fechada `t` usa solo información hasta `t`. Se **supone por verificar** que puede usarse al inicio de la sesión siguiente, `d=t+1`; no es hora de publicación demostrada ni necesariamente conservadora. El precio de referencia es el cierre ajustado de SPY de `d`, `A_d`, posterior a ese supuesto momento. El resultado usa `A_{d+1}...A_{d+10}`:

```text
etiqueta_d = 1 si min(A_{d+1}, …, A_{d+10}) / A_d - 1 <= -0.05
```

La fuente, campo, ajustes y zona horaria del cierre ajustado se registrarán antes de ejecutar. Las últimas diez decisiones sin horizonte completo no reciben etiqueta.

## Episodios, aciertos y falsas alarmas

Para cada etiqueta positiva, `brecha_d` es la primera sesión en `d+1...d+10` con `A <= 0.95*A_d`. Las brechas se agrupan recursivamente cuando están separadas por no más de cinco sesiones; cada grupo es un episodio, con inicio en su primera brecha y fin en la última. Su ventana de anticipación es `inicio-5...inicio-1`.

Una alerta en `d` es **acierto** si algún episodio inicia en `d+1...d+5`. Es **falsa alarma** si ninguno inicia en esa misma ventana. Una alerta más de cinco sesiones antes de un episodio no lo acredita; si no antecede otro episodio dentro de cinco sesiones, es falsa alarma. Una alerta en o después del inicio tampoco acredita. Una alerta solapada cuenta una vez para precisión/falsa alarma y puede aportar recall a ambos episodios; se reportará ese conteo.

## Particiones y fechas comunes

Se mantienen desarrollo 2020-01-02–2023-12-29, validación 2024-01-02–2024-12-31 y final 2025-01-02–2026-08-31. La partición se asigna por decisión `d`. Etiquetas pueden cruzar año con horizonte completo, pero episodios que cruzan fronteras se excluyen de métricas de episodios y se reportan; alertas no acreditan episodios de otra partición.

Se preservan los umbrales visibles de v1: `vol20 > P80_desarrollo(vol20)` y `z_skew252 >= 1.5`. La comparación primaria usa solo **fechas comunes** donde ambos scores existen y son elegibles para el mismo horizonte. Por partición se reportarán fechas esperadas, con `vol20`, con `z_skew252`, comunes y pérdidas específicamente por falta de skew.

En fechas comunes de desarrollo se congelan percentiles 90 de cada score, equivalentes a presupuesto de alertas de 10%, y se aplican sin recalibrar a validación/final. Se reporta frecuencia efectiva; empates y cambios de distribución pueden desviarla de 10%, sin reordenar datos futuros. Las reglas originales siguen visibles; las igual-frecuencia deciden lo primario.

## Calidad

Se conserva selección v2 y A3/A4. Sin respuesta, par o cotización utilizable no hay score de skew ni imputación; se registra pérdida de cobertura. `wide_spread`, salto extremo y cambio de vencimiento quedan en primario con bandera; exclusiones son sensibilidades separadas. `bid_zero`, `ask_below_bid` o cotización inválida impiden alerta. IV repetida se conserva sin redondear ni perturbar.

## Métrica y decisión

La métrica primaria es recall de episodios en fechas comunes y a igual frecuencia: episodios evaluables con alerta en sus cinco decisiones previas / episodios evaluables. Secundarias: cobertura, frecuencia efectiva, falsas alarmas con la misma ventana, precisión, anticipación, tasa base, cruces, solapamientos y sensibilidades.

**CANDIDATO** exige simultáneamente: ventaja de recall skew–benchmark `>=0.10` en validación y final; al menos 10 episodios finales; cobertura de skew en fechas comunes final `>=95%`; y falsas alarmas de skew no más de `0.02` sobre benchmark en final.

**INCONCLUSO:** menos de 10 episodios evaluables en final, sin importar métricas secundarias. No es STOP ni CANDIDATO; solo admite descriptivos y cobertura. Con 10 o más episodios, un fallo CANDIDATO puede ser AISLADO o STOP.

## Ambigüedades que bloquean congelamiento

1. Verificar o aceptar el supuesto de uso al inicio de `t+1` mientras la publicación EOD real es desconocida.
2. Aprobar fuente, campo y ajustes del cierre ajustado de SPY.
3. Aprobar 5%, diez sesiones y agrupación de brechas a cinco sesiones.
4. Aprobar o cambiar el crédito de una alerta a dos episodios solapados antes de resultados.
5. Aprobar presupuesto 10% y regla para empates si se requiere frecuencia exacta.
6. Confirmar que 95% de cobertura común no oculta pérdidas relevantes por falta de skew.
7. Aprobar umbrales CANDIDATO e INCONCLUSO antes de resultados.
8. Definir decisión humana, costos y oportunidades perdidas para Checkpoint C.

Hasta resolverlos, v2 no se congela. No se calculan etiquetas, métricas, desempeño ni HMM.
