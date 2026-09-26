# Propuesta v3 — primer experimento HMM A/B

Fecha: 2026-09-26  
Estado: propuesta; conserva v2. No entrena modelos ni calcula resultados.

## Elementos conservados

El evento sigue siendo caída de SPY >=7% en 20 sesiones desde `A_d`; hay dos estados; la salida primaria es `P(S[t+1]=r | observaciones_<=t)`; y la comparación primaria es HMM B con skew contra HMM A sin skew. La alerta se usa en `d=t+1` solo bajo supuesto EOD no verificado.

## Sesiones sin skew en HMM B

El calendario conserva cada sesión. En entrenamiento de B, una fila sin skew contribuye a la verosimilitud conjunta mediante las dimensiones observadas (retorno y `vol20`); la dimensión skew se marginaliza, es decir, no aporta término de emisión ni se imputa. La transición de estado entre esa sesión y las adyacentes se conserva.

En filtrado prospectivo, B primero avanza la distribución filtrada mediante la matriz de transición. Si skew falta, actualiza esa predicción con la emisión observada de retorno y `vol20`, marginalizando skew. Esa probabilidad se guarda como estado interno, pero B no emite alerta en esa fecha; la fecha cuenta como cobertura B perdida. A actualiza y puede alertar normalmente. No se comprime ni se salta el calendario.

## Episodios y ventanas incompletas

Brechas de -7% se agrupan a cinco sesiones como en v2. Los episodios cuya ventana de cinco decisiones previas contiene alguna sesión sin skew **permanecen** en el denominador del recall B. En esa sesión B equivale a ausencia de alerta; se cuentan por separado: episodios con ventana incompleta y número total de decisiones sin skew dentro de esas ventanas. A se evalúa con sus propias alertas en la misma ventana temporal.

## Fronteras de la ventana prospectiva de 12 meses

Sea `W=[w0,wN]` el primer y último día de decisión prospectivos y `F` las 20 sesiones de seguimiento posteriores a `wN`.

- Solo alertas emitidas en `W` entran a frecuencia, TAAE, precisión y recall.
- Se excluye del recall todo episodio cuyo inicio sea anterior a `w0+5`, porque su ventana completa de cinco decisiones no está dentro de `W`.
- Se incluyen episodios cuyo inicio esté entre `w0+5` y `wN+5`, siempre que tengan al menos una fecha de decisión en `W` que pueda alertarlos. Se observan precios hasta `wN+20` para conocer sus etiquetas.
- Se excluye episodio que inicia después de `wN+5`: ninguna alerta permitida de `W` puede acreditarlo.
- Alertas en los últimos cinco días de `W` se mantienen y se evalúan contra episodios que puedan iniciar hasta `wN+5`; por eso el informe espera las 20 sesiones de seguimiento.

Ejemplo inventado inicial: `w0=2027-01-04`; un episodio que inicia 2027-01-06 se excluye porque faltan decisiones prospectivas previas. Uno que inicia 2027-01-12 sí entra, con ventana 2027-01-05...2027-01-11.

Ejemplo inventado final: `wN=2027-12-31`; alerta del 2027-12-30 puede acreditar episodio que inicia 2028-01-05 y se observa durante seguimiento. Un episodio que inicia 2028-01-10 se excluye porque queda a más de cinco decisiones de la última alerta permitida.

## Tasa de alertas no acreditadas

La proporción se llama **Tasa de Alertas No Acreditadas a Episodio (TAAE)**:

```text
TAAE = número de alertas emitidas sin episodio asignado / número de alertas emitidas
```

Una alerta es asignada como máximo al primer episodio cronológico cuyo inicio cae en sus cinco decisiones posteriores. Si no recibe asignación, integra el numerador TAAE. Si no hay alertas emitidas, TAAE se reporta como no definida, no como cero.

El límite congelado de utilidad es `TAAE_B <= TAAE_A + 0.02` en la ventana prospectiva. Este es exactamente el límite de dos puntos porcentuales frente a A; no se cambia por frecuencia observada ni por resultados.

Ejemplo inventado: A emite 20 alertas y 15 no se acreditan, por lo que `TAAE_A=0.75`. B emite 18 y 14 no se acreditan, `TAAE_B=0.7778`; B cumple porque `0.7778 <= 0.77` es falso, por lo que en realidad no cumple. El ejemplo ilustra que 2 puntos son 0.02, no 2% relativo.

## Bloqueos restantes de implementación

1. Confirmar fuente concreta y fecha de inicio `w0` de la primera ventana prospectiva no observada.
2. Aprobar el supuesto de publicación EOD antes de abrir `t+1`.
3. Confirmar que la implementación HMM soportará emisiones gaussianas parcialmente observadas con marginalización, no imputación.
4. Aprobar la lista exacta de semillas y el software/versión que realizará el ajuste reproducible.
5. Confirmar que el criterio económico de -7%/20 sesiones y 10% de alertas justifica la revisión humana.

Hasta resolverlos no se entrenan modelos ni se calculan resultados.
