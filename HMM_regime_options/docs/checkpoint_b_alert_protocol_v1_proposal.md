# Checkpoint B — protocolo de alerta v1 propuesto

Fecha: 2026-09-26  
Estado: **propuesta para aprobación y congelamiento. No se han calculado
etiquetas, asociaciones ni desempeño.** Conserva el borrador v0 como antecedente.

## 1. Pregunta y alcance

¿Una alerta binaria basada en el skew diario de SPY identifica episodios de
caída posteriores mejor que un benchmark basado solo en precios de SPY, bajo el
mismo reloj de decisión y la misma frecuencia de alertas?

La evaluación es exclusivamente de alerta histórica. No prueba causalidad del
skew, no indica operaciones, no evalúa Actinver y no entrena HMM.

## 2. Reloj de información y precio de referencia

Para una cadena y variables fechadas en sesión `t`:

1. La señal se calcula solo con datos de fecha `t` y ventanas que terminan en
   `t`.
2. Por ausencia de un timestamp EOD histórico verificable, la señal se declara
   utilizable **al inicio de la siguiente sesión regular de EE. UU., `d=t+1`**.
   Es un supuesto conservador de investigación, no una hora de publicación
   demostrada.
3. El precio de referencia es el **cierre ajustado de SPY en `d`**, denotado
   `A_d`. Ese cierre ocurre después de que la señal puede utilizarse al inicio
   de `d`; por tanto, no es información disponible para construir la señal.
4. La ventana de resultado contiene los diez cierres ajustados posteriores al
   precio de referencia: `A_{d+1}, …, A_{d+10}`. Ningún precio de esa ventana
   entra en una variable de la señal de `t`.

Este reloj evita usar el cierre de `t` como base de un evento que se atribuya a
una decisión disponible solo en `t+1`.

## 3. Etiqueta operacional propuesta: caída posterior a 10 sesiones

Para cada fecha de decisión `d` con diez sesiones futuras observables:

```text
drawdown_d = min(A_{d+1}, …, A_{d+10}) / A_d - 1
etiqueta_d = 1 si drawdown_d <= -0.05; en otro caso, 0
```

`A` es el cierre ajustado de la serie diaria de SPY. Se debe registrar la fuente
exacta, campo, ajustes por dividendos/splits y zona horaria antes de ejecutar.
Las últimas diez fechas de decisión con horizonte incompleto no reciben etiqueta
y no entran en métricas de resultado.

## 4. Inicio, fin y agrupación de episodios

Una etiqueta positiva no equivale por sí sola a un episodio independiente. Para
evitar contar repetidamente la misma caída:

1. Para cada `d` con `etiqueta_d=1`, guardar `brecha_d`: primera sesión en
   `d+1…d+10` cuyo cierre ajustado sea `<= 0.95 * A_d`.
2. Ordenar las etiquetas positivas por `brecha_d`.
3. Iniciar un episodio en la primera `brecha_d` no asignada.
4. Añadir al mismo episodio toda etiqueta positiva posterior cuya `brecha_d`
   esté a no más de **cinco sesiones de mercado** de la última brecha asignada.
   Repetir hasta que no queden brechas dentro de esa distancia.
5. El inicio del episodio es la primera brecha del grupo; el fin es la última.
   Ese grupo cuenta como **un** evento para métricas basadas en episodios.

La ventana de alerta de un episodio son las cinco fechas de decisión previas a
su inicio: `inicio-5 … inicio-1`. Solo una alerta emitida en esa ventana cuenta
como anticipación; una alerta en o después del inicio no cuenta como alerta
anticipada de ese episodio.

## 5. Fronteras temporales

Las particiones propuestas son desarrollo (2020–2023), validación (2024) y
evaluación final (2025–2026-08), con límites exactos registrados antes de
calcular. Para evitar fugas entre ellas:

- Una fecha de decisión pertenece a su partición por su fecha `d`, no por la
  fecha de la cadena `t`.
- Una etiqueta se puede calcular si sus diez cierres futuros existen, aunque
  crucen año calendario; se conserva en la partición de `d`.
- Para la métrica de episodios, se excluye de cada partición cualquier episodio
  cuyo inicio o fin cruce una frontera de partición. Se informa el número
  excluido por frontera.
- Alertas en una partición no pueden acreditar un episodio de otra partición.
- La evaluación final no ajusta ventanas, umbrales ni reglas usando sus precios
  o etiquetas.

## 6. Reglas de alerta y comparación a igual frecuencia

### Umbrales originales visibles

Estas reglas se reportarán tal como fueron propuestas, con su frecuencia
observada por partición:

```text
benchmark_original_t = 1 si vol20_t > percentil 80 de vol20 en desarrollo
skew_original_t      = 1 si z_skew252_t >= 1.5
```

`vol20_t` es la desviación estándar de retornos log de SPY en las últimas 20
sesiones disponibles hasta `t`. `z_skew252_t` usa media y desviación estándar
del skew de las 252 sesiones disponibles hasta `t`, sin información posterior.

### Comparación primaria a frecuencia igual

La comparación primaria no usa los umbrales originales para declarar ganador.
Usa un presupuesto común de alertas de **10% de las fechas de desarrollo con
señal disponible**:

- Para cada score (`vol20` y `z_skew252`), fijar en desarrollo su percentil 90
  como umbral de frecuencia equivalente.
- Congelar ambos valores numéricos y aplicarlos sin recalibración a validación y
  evaluación final.
- Reportar la frecuencia efectiva en cada partición; puede desviarse de 10% por
  empates, faltantes o cambio de distribución. No se reordena la muestra final
  para forzar la frecuencia.

Las cuatro reglas (dos originales y dos igual-frecuencia) permanecen visibles.
La conclusión primaria solo compara las dos reglas igual-frecuencia.

## 7. Calidad y faltantes

Se conserva la selección v2 y las reglas A3/A4, sin excluir observaciones de
la serie primaria por haber visto resultados:

- Sin respuesta, sin par o cotización no utilizable: no hay alerta; no se
  imputa skew; se informa cobertura.
- `wide_spread`, salto extremo o cambio de vencimiento: la observación queda en
  el análisis primario con bandera; las exclusiones son solo sensibilidades
  preespecificadas y separadas.
- `bid_zero`, `ask_below_bid` o bid/ask inválidos: no hay alerta y se informa
  el motivo.
- IV repetida: se conserva sin redondear ni perturbar; se reporta su frecuencia.

## 8. Métrica primaria y criterio inequívoco de CANDIDATO

### Métrica primaria

**Recall de episodios a frecuencia igual:** proporción de episodios evaluables
que tuvieron al menos una alerta en su ventana de cinco decisiones previas.
Se calcula por separado para benchmark y skew con los umbrales de percentil 90
congelados en desarrollo.

### Criterio CANDIDATO

La señal de skew será **CANDIDATO para investigación adicional** solo si se
cumplen simultáneamente estas cuatro condiciones, sin excepciones:

1. En validación y en evaluación final, el recall de episodios de skew menos el
   del benchmark es `>= 0.10` (diez puntos porcentuales).
2. En evaluación final hay al menos 10 episodios evaluables.
3. La cobertura de fechas con señal de skew en evaluación final es `>= 95%`.
4. En evaluación final, la tasa de falsas alarmas de skew no supera a la del
   benchmark por más de `0.02` (dos puntos porcentuales).

Si hay menos de 10 episodios finales, o si falla cualquiera de las cuatro
condiciones, el resultado no puede ser CANDIDATO: será AISLADO o STOP según las
métricas secundarias y limitaciones declaradas.

## 9. Métricas secundarias

- Frecuencia de alertas de las cuatro reglas y cobertura de señal.
- Anticipación: sesiones entre la primera alerta válida y el inicio de cada
  episodio alertado.
- Tasa de falsas alarmas: alertas sin episodio iniciado en sus diez sesiones
  posteriores; el denominador excluye fechas sin horizonte completo.
- Precisión de alerta y tasa base de etiquetas.
- Número de episodios, etiquetas positivas, episodios excluidos por fronteras
  y alertas solapadas.
- Resultados de sensibilidad para `wide_spread` y saltos/cambios de vencimiento.

No se calcularán probabilidades ni calibración con estas reglas binarias.

## 10. Decisiones económicas abiertas para revisión humana

Antes de congelar v1 deben aprobarse explícitamente:

1. Si una caída máxima de 5% y diez sesiones representa un riesgo relevante
   para la revisión humana pretendida; no se asume que sea una regla de cartera.
2. Si el momento de decisión “inicio de `t+1`” es aceptable mientras falta el
   timestamp EOD del proveedor, y si el cierre ajustado de `t+1` es la base
   económica apropiada del resultado.
3. Si agrupar brechas separadas por hasta cinco sesiones representa un episodio
   económico razonable o si el intervalo debe cambiarse antes de calcular.
4. Si 10% de presupuesto de alertas refleja una carga de revisión humana
   factible; el valor no debe optimizarse con desempeño observado.
5. Si las condiciones CANDIDATO (10 pp de recall, 2 pp de falsas alarmas y 10
   episodios finales) son suficientemente exigentes y operativamente útiles.
6. Qué decisión humana concreta podría informar una alerta prometedora y qué
   costos/oportunidades perdidas habría que evaluar en Checkpoint C.

Hasta esta aprobación, v1 es una propuesta. **No se calcularán etiquetas,
asociaciones, desempeño ni HMM.**
