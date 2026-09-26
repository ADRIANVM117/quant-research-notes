# Corrección separada — frontera final de la propuesta HMM v3

Fecha: 2026-09-26  
Alcance: corrige únicamente la frontera final de `hmm_first_experiment_v3_proposal.md`. La v3 se conserva sin cambios. No entrena HMM ni calcula resultados reales.

## Definición original y tres índices distintos

Para cada fecha de decisión `d`, sea `A_d` su cierre ajustado. La etiqueta busca la **primera fecha de brecha** `b` en `d+1, ..., d+20` que cumpla:

```text
A_b / A_d - 1 <= -0.07.
```

Si no existe esa fecha, la decisión `d` no genera brecha. El 20 es el máximo horizonte de búsqueda desde `d`; no significa que la referencia de una brecha fechada `b` sea `A_b` ni que deba compararse con `A_{b+20}`.

Esta nota usa tres índices, que no se intercambian:

| Símbolo | Significado |
|---|---|
| `d` | fecha de decisión y cierre de referencia `A_d`; la alerta calculada tras `d-1` queda disponible en `d` solo bajo el supuesto EOD no verificado. |
| `b(d)` | primera fecha futura, dentro de `d+1...d+20`, que cruza el umbral respecto de `A_d`. |
| `s` | inicio de episodio agrupado: la primera fecha de brecha de un bloque de fechas de brecha separadas por como máximo cinco sesiones. |

Puede haber varias decisiones `d` con la misma `b(d)`, y varias fechas de brecha dentro del mismo episodio. Para formar episodios se deduplican las fechas de brecha `b(d)`, se ordenan y se agrupan por distancia entre fechas consecutivas de cinco sesiones o menos. El inicio `s` es la primera fecha del grupo.

## Frontera de acreditación con `wN=0`

Sea `wN=0` la última fecha de decisión prospectiva. Una alerta emitida en `j` se asigna, como máximo, al primer episodio cuyo inicio `s` caiga en `j+1, ..., j+5`. Por tanto, la alerta de `0` solo puede acreditarse a un episodio cuyo inicio esté en `+1...+5`.

Para saber si existe un inicio de episodio en ese intervalo se deben inspeccionar las fechas de brecha candidatas `b=+1, ..., +5`. Para una fecha concreta `b`, las únicas decisiones que pueden tener `b(d)=b` son:

```text
d = b-20, ..., b-1.
```

Así, para `b=+5` se revisan las decisiones `-15, ..., +4`, sus referencias `A_d` y todos los cierres de cada tramo `d+1, ..., +5` necesarios para confirmar que `+5` fue su **primera** brecha. No interviene una decisión `+5`, y no se usa `A_{+5}` como referencia salvo que `+5` sea la propia decisión de otra etiqueta futura, que no puede producir una brecha fechada `+5`.

Con el calendario y los cierres anteriores completos, el último cierre futuro necesario para decidir si hay algún inicio `s` en `+1...+5` es `A_{+5}`. No se necesita `A_{+20}` ni `A_{+25}` para esa pregunta: una brecha se reconoce en el día en que ocurre al contrastarla con su referencia pasada. Si falta alguno de los cierres requeridos para determinar si `b` fue la primera brecha de las decisiones aplicables, la fecha de brecha y toda alerta que dependa de ella quedan censuradas; no se presuponen como ausencia de episodio.

Visto desde la asignación, un inicio en `+5` puede acreditar alertas emitidas en `0`, `+1`, `+2`, `+3` o `+4`; una alerta emitida en `+5` no puede acreditarlo porque el inicio no está en una de sus cinco sesiones posteriores.

## Cierre recursivo o censura del episodio

Una vez identificado un episodio cuyo último día de brecha conocido es `last`, se inspeccionan las cinco sesiones siguientes `last+1, ..., last+5` para ver si aparece alguna nueva **fecha de brecha**. Cada una se determina con el mismo procedimiento anterior: referencias de decisiones situadas entre 20 y 1 sesiones antes y el cierre de esa fecha; no se espera 20 sesiones posteriores a ella.

- Si ninguna de esas cinco fechas es brecha y todos los cierres necesarios están disponibles, el episodio se declara **cerrado** al final de `last+5`.
- Si aparece una brecha en una de ellas, se incorpora al mismo episodio, `last` pasa a ser esa nueva fecha y se reinicia la inspección de cinco sesiones. La regla puede repetirse; no tiene un número máximo de extensiones.
- El episodio queda **censurado a la derecha** si termina la serie de cierres o falta un cierre necesario antes de completar cinco sesiones no brecha después del `last` vigente. No se infiere un cierre de la ausencia de datos.

Por tanto, `+25` no es un seguimiento universalmente suficiente. Para la acreditación de la alerta final `0`, es innecesario: `+5` basta si los precios requeridos existen. Para **cerrar** un episodio que inicia en `+5`, el mínimo es `+10` solo si no aparecen extensiones; si aparece una extensión en `+9`, se requiere como mínimo hasta `+14`; si continúa extendiéndose, el cierre exige cinco sesiones tras la última brecha y puede caer más allá de `+25`. No se fija un horizonte artificial: se sigue hasta cierre recursivo o se marca censura.

## Efecto preespecificado en recall y TAAE

- Un episodio con inicio `s` confirmado dentro del rango admisible de recall permanece en su denominador aunque su final esté censurado. Se informa la bandera `episode_right_censored`, la última fecha de brecha confirmada y el motivo. Su acierto depende de una alerta admisible en las cinco decisiones previas a `s`, no de conocer la duración final del episodio.
- Una alerta se acredita en cuanto se confirma el primer inicio de episodio admisible en sus cinco sesiones posteriores. Una extensión posterior, incluso censurada, no revoca la acreditación ni altera la TAAE.
- Una alerta se clasifica como no acreditada únicamente si las cinco fechas de inicio posibles se resolvieron sin inicio de episodio. Si falta un cierre o una clasificación de primera brecha impide resolver alguna de esas cinco fechas, la alerta es `alert_right_censored=1`; queda fuera tanto del numerador como del denominador de TAAE y se informa aparte. No se denomina falsa alarma.

En particular, para la alerta de `0`, precios completos hasta `+5` resuelven su acreditación o no acreditación. El cierre posterior del episodio no cambia su contribución a TAAE. Las alertas de `-4, ..., 0` se tratan análogamente: la fecha máxima que puede necesitar una alerta `j` para acreditar o descartarse es `j+5`, sujeto a disponer de los cierres históricos de sus decisiones de referencia.

## Ejemplo inventado de frontera final

Supóngase `wN=0`, cierres completos hasta `+14`, y una alerta B emitida en la **fecha de decisión** `d=0`.

| Índices y hecho inventado | Resultado de la regla |
|---|---|
| `d=0` | La alerta puede acreditarse solo a inicios de episodio `s=+1...+5`. |
| `d=-3`, `b(d)=+5` | Al comparar `A_{+5}` con `A_{-3}`, `A_{+5}/A_{-3}-1=-7.4%`; no hubo cruce entre `-2` y `+4`. La **fecha de primera brecha** es `b=+5`, no una comparación entre `A_{+5}` y `A_{+25}`. |
| `s=+5` | Como no existe una fecha de brecha anterior dentro de cinco sesiones que la una a un grupo previo, `+5` es el **inicio del episodio agrupado**. La alerta `d=0` queda acreditada al confirmarse `A_{+5}`. |
| `d=+4`, `b(d)=+9` | `A_{+9}/A_{+4}-1=-7.1%` y no hubo cruce en `+5...+8`. La nueva fecha de brecha `+9` está a cuatro sesiones de `+5`, por lo que extiende el mismo episodio; `last=+9`. |
| Cierres `+10...+14` | Si ninguna fecha es brecha, el episodio queda cerrado en `+14`. Si falta alguno, o si aparece otra brecha, no se declara cerrado: se censura o se reinicia el conteo desde la nueva `last`, respectivamente. |

Este ejemplo separa la fecha de decisión `d`, la primera fecha de brecha `b(d)` y el inicio agrupado `s`. Con datos solo hasta `+5`, la TAAE de la alerta `0` puede ya resolverse; con datos hasta `+14` se cierra este episodio concreto solo porque su última extensión fue `+9` y luego hubo cinco sesiones completas sin brecha.

## Sustitución operativa de la frase de seguimiento final

Para la implementación futura, la frase de v3 “se observan precios hasta `wN+20`” debe leerse, para la frontera final, así:

> Para acreditar o descartar alertas de la última decisión `wN`, se mantienen cierres ajustados hasta `wN+5` y los cierres históricos necesarios para identificar primeras brechas. La duración de un episodio se sigue recursivamente hasta observar cinco sesiones consecutivas sin fecha de brecha después de su última brecha, o se declara censurada si la observación termina antes. Ningún horizonte fijo, incluido `wN+20` o `wN+25`, basta por sí solo para garantizar el cierre de todos los episodios.

No cambia el evento de caída de 7% en 20 sesiones, los dos estados, las reglas de HMM ni la comparación primaria B contra A de la v3.
