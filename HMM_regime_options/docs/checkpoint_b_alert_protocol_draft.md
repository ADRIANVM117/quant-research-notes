# Checkpoint B — protocolo borrador de alerta v0

Fecha: 2026-09-26  
Estado: **borrador para aprobación; no congelado y sin resultados calculados.**

## Propósito y pregunta acotada

Evaluar si una señal diaria construida con el skew de opciones de SPY aporta
una alerta temprana de una caída futura, frente a una referencia que usa solo
precios pasados de SPY. Este documento define el experimento antes de producir
etiquetas, asociaciones o métricas.

No evalúa causalidad económica del skew, no recomienda operaciones y no
autoriza un HMM. El HMM solo podría considerarse en un experimento posterior
si la señal sencilla supera los criterios acordados.

## 1. Evento futuro propuesto

Para una fecha de señal `t`, se propone etiquetar **evento de caída a 10
sesiones** cuando el peor cierre ajustado de SPY durante `t+1` a `t+10` sea al
menos 5% inferior al cierre ajustado de `t`:

```text
evento_t = 1 si min(CierreAjustado[t+1:t+10]) / CierreAjustado[t] - 1 <= -0.05
```

El intervalo es estrictamente futuro: ninguna de esas diez sesiones entra en
la construcción de variables de fecha `t`. La etiqueta solo existe al terminar
la décima sesión futura, por lo que no se utiliza como información disponible
en `t`.

**Límite.** El umbral de 5% y el horizonte de 10 sesiones son propuestas de
diseño, no hallazgos. La definición no mide una pérdida realizada ni incorpora
costos, instrumentos mexicanos o decisiones de Actinver.

## 2. Reloj de decisión propuesto

- La cadena y el cierre de SPY llevan fecha `t`.
- Dado que no existe un timestamp histórico verificable de publicación EOD, la
  señal de `t` se considera disponible para una decisión humana **a partir de
  la siguiente sesión de mercado, `t+1`**.
- Una alerta de `t` nunca se atribuye a una decisión tomada al cierre de `t`.
- Para cada observación se guardarán fecha de cadena, fecha de precio, fecha
  efectiva de decisión (`t+1`) y el supuesto de disponibilidad.

**Límite.** Esto evita anticipar información, pero sigue siendo un supuesto
conservador hasta verificar el horario de publicación del proveedor.

## 3. Universo y partición temporal propuesta

Se parte del tramo auditado 2020-01-02 a 2026-08-31, sin rellenar días sin par.
La propuesta de partición cronológica es:

| Uso | Periodo propuesto | Finalidad |
|---|---|---|
| Desarrollo | 2020-01-02 a 2023-12-29 | Fijar transformaciones y umbrales. |
| Validación temporal | 2024-01-02 a 2024-12-31 | Elegir, una sola vez, entre reglas preespecificadas. |
| Evaluación final | 2025-01-02 a 2026-08-31 | Informe final sin reajustar parámetros. |

Toda ventana móvil en una fecha usa solo información disponible hasta esa
fecha. Si una decisión cambia después de ver la validación, se registra como
un experimento nuevo y la evaluación previa deja de ser final.

**Límite.** El periodo final es más corto que los anteriores y puede contener
pocos eventos bajo la definición propuesta; no se debe ampliar o mover después
de mirar desempeño.

## 4. Benchmark sin opciones propuesto

El benchmark será una regla de volatilidad realizada sin opciones:

```text
vol20_t = desviación estándar de retornos log diarios de SPY en t-19:t
alerta_benchmark_t = 1 si vol20_t supera el percentil 80 de vol20
                     calculado únicamente en el periodo de desarrollo
```

El percentil se congela después de desarrollo y no se recalcula con validación
ni evaluación final. El benchmark usa el mismo reloj de decisión que el skew.

**Límite.** Es una referencia deliberadamente simple, no un modelo óptimo de
riesgo. Su función es comprobar valor incremental, no maximizar desempeño.

## 5. Señal sencilla de skew propuesta

Se usa el `skew_t = IV_put - IV_call` de la selección v2 ya congelada: mismo
vencimiento, 21–45 DTE, deltas objetivo ±0.25 y desempates documentados.

Propuesta de regla:

```text
z_skew_t = (skew_t - media_252_t) / desviación_estándar_252_t
alerta_skew_t = 1 si z_skew_t >= 1.5
```

Las ventanas terminan en `t`; los parámetros 1.5 y 252 se fijan antes de
calcular desempeño. La comparación primaria será de la alerta de skew contra
el benchmark, no una combinación optimizada de ambos.

**Límite.** La estandarización presupone suficiente historia previa y no
resuelve por sí misma discontinuidades de selección o precisión limitada de IV.

## 6. Tratamiento preespecificado de calidad

| Situación | Serie primaria | Registro y sensibilidad |
|---|---|---|
| Sin respuesta, sin par elegible o sin cotización utilizable | No producir alerta; no imputar skew. | Reportar cobertura y excluir solo esa fecha del denominador de métricas de alerta. |
| `wide_spread` | Mantener la observación y su skew en la serie primaria. | Etiquetar la fecha; análisis de sensibilidad opcional que excluya esas fechas, registrado como variante separada. |
| `bid_zero`, `ask_below_bid`, bid/ask inválido | No producir alerta. | Reportar motivo; no sustituir precios ni IV. |
| Salto extremo de skew o cambio de vencimiento | Mantener la observación. | Etiquetar ambos campos y publicar métricas con y sin el subconjunto marcado solo como sensibilidad separada. |
| IV textualmente repetida | Mantener la observación. | Reportar frecuencia; no redondear ni perturbar valores. |

La regla v2 no cambia por estas banderas. Ninguna exclusión de sensibilidad
puede reemplazar el resultado primario ni definirse después de observar sus
métricas.

**Límite.** Las sensibilidades no determinan cuál señal es “verdadera”; solo
exponen cuánto depende el resultado de condiciones de calidad conocidas.

## 7. Métricas preespecificadas

Para cada regla y cada partición, informar:

1. **Cobertura:** fechas con señal disponible / fechas esperadas, y fracción
   con banderas de calidad.
2. **Sensibilidad a eventos:** eventos con al menos una alerta en las cinco
   sesiones anteriores al inicio del evento, dividido entre eventos evaluables.
3. **Anticipación:** número de sesiones entre la primera alerta válida y el
   inicio del evento, resumido solo para eventos alertados.
4. **Falsas alarmas:** alertas que no son seguidas por un evento en las diez
   sesiones futuras, dividido entre alertas evaluables.
5. **Precisión de alerta:** alertas seguidas por evento / alertas evaluables.
6. **Tasa base de eventos:** eventos / fechas evaluables, para contextualizar
   precisión y falsas alarmas.

No se informarán métricas de probabilidad o calibración porque las reglas
propuestas producen alertas binarias. Si se introducen probabilidades, se
creará un protocolo nuevo que añada Brier score y calibración.

**Límite.** Alertas cercanas pueden solaparse alrededor del mismo episodio;
el informe debe declarar el conteo de eventos y no presentar métricas aisladas
como evidencia suficiente.

## 8. Criterios de decisión propuestos

- **STOP por señal:** el skew no mejora sensibilidad, anticipación o falsas
  alarmas frente al benchmark en evaluación final, o su cobertura es insuficiente.
- **AISLADO:** existe diferencia exploratoria, pero no se sostiene en la
  evaluación final o depende materialmente de banderas de calidad.
- **CANDIDATO para investigación adicional:** mejora preespecificada frente al
  benchmark en evaluación final, con cobertura declarada y sin depender de
  variantes seleccionadas retrospectivamente.

No se fijan aún magnitudes numéricas de mejora para “CANDIDATO”; esa omisión es
una decisión pendiente y bloquea el congelamiento.

## Decisiones que debemos aprobar antes de congelar

1. Confirmar evento: ¿caída máxima de 5% sobre cierre ajustado en 10 sesiones,
   o otro umbral/horizonte? Elegir uno sin inspeccionar etiquetas.
2. Confirmar la fuente y definición de **cierre ajustado**; A4 auditó precios
   diarios, pero esta transformación debe quedar documentada y reproducible.
3. Aprobar la partición 2020–2023 / 2024 / 2025–2026-08 o sustituirla por otra
   justificada antes de calcular resultados.
4. Aprobar benchmark `vol20` y percentil 80, o una única referencia alternativa
   sin opciones.
5. Aprobar señal `z_skew` con ventana 252 y umbral 1.5, incluyendo el mínimo de
   historia requerido para emitir una alerta.
6. Fijar la mejora mínima requerida frente al benchmark y el máximo tolerable de
   falsas alarmas para pasar a CANDIDATO.
7. Decidir si las sensibilidades por `wide_spread` y saltos/cambios de
   vencimiento serán obligatorias; si lo son, mantenerlas exactamente como
   variantes secundarias descritas arriba.
8. Confirmar que el supuesto de decisión en `t+1` es aceptable mientras no se
   disponga del timestamp EOD del proveedor.

Hasta aprobar estos puntos, este archivo es un borrador y **no debe usarse para
calcular etiquetas, asociaciones, desempeño ni entrenar modelos**.
