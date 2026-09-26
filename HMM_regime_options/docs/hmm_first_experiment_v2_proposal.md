# Propuesta v2 — primer experimento HMM A/B

Fecha: 2026-09-26  
Estado: propuesta separada de Checkpoint B y Actinver. No autoriza entrenar HMM ni calcular resultados.

## Resultado futuro y episodios

Para decisión `d=t+1`, el evento es una caída de SPY de al menos 7%: `min(A[d+1...d+20])/A[d]-1 <= -0.07`, donde `A` es cierre ajustado. No reutiliza automáticamente el evento B.

Cada etiqueta positiva guarda `brecha_d`, la primera sesión futura que cruza el -7%. Las brechas se ordenan y se agrupan recursivamente si la siguiente está a no más de cinco sesiones de mercado de la última brecha del grupo. Cada grupo es un episodio independiente; empieza en la primera brecha y termina en la última. Su ventana de anticipación son exactamente las cinco decisiones previas al inicio: `inicio-5...inicio-1`.

Una alerta en decisión `d` es acierto si existe episodio que inicia en `d+1...d+5`; es falsa alarma si no existe. Los denominadores son: recall = episodios evaluables; falsa-alarma = alertas emitidas; precisión = alertas emitidas. Una alerta se asigna como máximo al primer episodio cronológico en su ventana de cinco sesiones. Alertas fuera de esa ventana no acreditan episodios y son falsas alarmas si no acreditan otro.

## Reloj congelado

Las observaciones llegan hasta el cierre de `t`. La alerta está disponible en `d=t+1` solo bajo el supuesto de publicación EOD aún no verificado. La caída se mide desde `A_d`, cierre ajustado de `d`; el movimiento intradía o de cierre durante `d` queda fuera del resultado definido.

## Modelos y filtro

Modelo A es HMM gaussiano de dos estados con retorno log diario y `vol20`. Modelo B recibe las mismas variables y skew v2. `vol20` es desviación estándar muestral de retornos log de las últimas 20 sesiones, incluyendo `t`, con mínimo 20 observaciones. Retornos, `vol20` y skew se transforman con media y desviación estándar calculadas solo en desarrollo; esas constantes se congelan para cualquier aplicación posterior.

La salida primaria es `P(S[t+1]=r | observaciones_<=t)`, probabilidad predictiva de un paso. El estado `r` se llama descriptivamente **estado de mayor volatilidad**: se identifica solo en desarrollo como el de mayor media estandarizada de `vol20`; empate por menor retorno medio. Que anticipe caídas es hipótesis, no definición.

Con skew faltante en B, el calendario no se comprime: se aplica transición predictiva desde el último filtro, pero no actualización de emisión de B; se guarda la probabilidad como estado interno, no se emite alerta de B y la fecha cuenta como pérdida de cobertura B. A continúa con su actualización normal. No hay imputación de skew ni alerta retroactiva.

Semillas se fijan como una lista preespecificada de 10 enteros `0...9`. Se elige la semilla con mayor log-verosimilitud de desarrollo; empate por semilla menor. Si todo ajuste falla, se registra fallo, B no emite alertas y el experimento queda INCONCLUSO por cobertura. No se elige semilla con métricas futuras.

## Cambios de etiqueta entre ajustes

Si se aprueba reajuste posterior, se identifica de nuevo el estado de mayor volatilidad con la regla anterior. Se guardan medias de emisión, transiciones y mapeo. Las etiquetas se alinean con el ajuste previo por mínima distancia euclídea entre medias; si el emparejamiento no es único, se declara ruptura y no se concatenan alertas. Para la evaluación prospectiva propuesta no hay reajustes.

## Fechas comunes y umbrales

La comparación primaria B contra A usa solo fechas comunes donde ambos producen probabilidad predictiva, existe horizonte de 20 sesiones y la decisión pertenece a la misma partición. En desarrollo, sobre esas fechas, el umbral de cada modelo es su percentil 90; empates se incluyen (`>=`). Estos dos valores se congelan. Frecuencia efectiva prospectiva se reporta aparte de cobertura perdida: fechas elegibles, fechas A disponibles, fechas B disponibles, fechas comunes y pérdidas B por skew faltante/fallo.

## Evaluación prospectiva

El periodo 2020–2026 ya fue visto y solo sirve para desarrollo exploratorio. La evaluación confirmatoria empieza el **primer día de mercado posterior al cierre de los parámetros congelados** y termina el último día de mercado doce meses después. Las etiquetas se conocen solo al cierre de la vigésima sesión posterior a cada decisión; por ello el informe final se emite tras esperar 20 sesiones adicionales. Durante esos doce meses no se reentrena, recalibra ni redefine eventos.

Si al cierre hay menos de 10 episodios independientes evaluables, la decisión es **INCONCLUSO**. No se cambian umbrales, horizonte ni evento para evitarlo.

## Criterios y decisiones abiertas

Para utilidad prospectiva: cobertura B >=95% de fechas elegibles, frecuencia de alertas entre 8% y 12%, y reporte separado de banderas. Investigación adicional requiere que B supere A en recall por >=10 puntos porcentuales sin aumentar falsas alarmas por más de 2 puntos, con al menos 10 episodios.

Queda por aprobar: pertinencia económica de -7%/20 sesiones; carga humana de 10% de alertas; consecuencia humana no automática; aceptabilidad del supuesto EOD; costo de falsos positivos; fuente exacta de la próxima ventana prospectiva; y si el HMM gaussiano de dos estados es una simplificación aceptable.

No se entrenarán HMM ni se calcularán etiquetas, episodios o desempeño hasta aprobar estas decisiones.
