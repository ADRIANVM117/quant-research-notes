# Propuesta — primer experimento HMM de regímenes

Fecha: 2026-09-26  
Estado: propuesta separada; no autoriza entrenar ni calcular resultados.

## Pregunta y resultado futuro

¿Añadir skew de opciones a un HMM pequeño mejora una alerta prospectiva de un entorno en el que SPY sufrirá una caída material en el siguiente mes de mercado?

El resultado observable propuesto no reutiliza B: para decisión `d=t+1`, hay evento si el mínimo cierre ajustado de SPY en las 20 sesiones `d+1...d+20` es al menos 7% inferior al cierre ajustado de `d`. Este resultado representa una revisión humana de exposición a una caída mensual material, no una orden ni un régimen “verdadero”.

## Modelo y observaciones en cada fecha

Se propone un HMM gaussiano de **dos estados**, con parámetros ajustados solo en entrenamiento. Modelo A recibe retorno log diario y volatilidad realizada `vol20`, ambos hasta `t`. Modelo B recibe exactamente esas variables más skew v2 hasta `t`. El skew faltante no se imputa: esa fecha no recibe salida del Modelo B y queda en cobertura perdida. Banderas de calidad se conservan para sensibilidad.

Transformaciones, escalamiento, tratamiento de faltantes, número de estados, semillas y fechas de reentrenamiento se congelan antes de ajustar. Los comparadores reciben solo su información admisible: `vol20` recibe precios pasados; skew simple recibe skew v2; Modelo A no recibe opciones; Modelo B sí recibe skew además de las variables de A.

## Salida primaria y etiqueta del estado

La salida primaria será la probabilidad predictiva de un paso de estar en estado de riesgo: `P(S_{t+1}=r | observaciones_<=t)`. Es prospectiva y puede usarse desde `t+1` bajo el supuesto no verificado de disponibilidad EOD.

El estado `r` se identifica exclusivamente en entrenamiento como el estado con mayor media ajustada de `vol20` estandarizada. Si hay empate exacto, se escoge el de menor media de retorno. No se usan eventos futuros para etiquetar estados.

Las probabilidades **filtradas** usan solo datos hasta `t`; son las únicas válidas para alertas históricas. Estados suavizados usan datos posteriores y solo pueden aparecer en un anexo descriptivo, nunca en métricas de alerta.

Ante cada nuevo ajuste, se vuelve a aplicar la regla anterior. Para evitar cambio de etiquetas, se guardan medias de emisión, matriz de transición y regla de mapeo; se alinea cada nuevo estado con el previo por menor distancia euclídea de medias de emisión antes de informar series. Si no hay correspondencia única, se declara ruptura y no se concatena la alerta.

## Comparación incremental y alertas

Los cuatro comparadores son: Modelo A HMM sin skew; Modelo B HMM con skew; `vol20` simple; y skew simple. Cada uno usa su score prospectivo o contemporáneo admisible. La comparación incremental primaria es B contra A, en fechas comunes donde ambos HMM producen score. Las comparaciones con reglas simples usan sus fechas comunes respectivas y se reportan separadamente.

En desarrollo se congelan umbrales que producen 10% de alertas en fechas comunes; se aplican sin recalibrar. Se reporta frecuencia efectiva, cobertura y empates. La alerta HMM es `1` si su probabilidad predictiva supera el umbral congelado.

## Evaluación prospectiva viable

Como 2020–2026 ya fue inspeccionado, cualquier ajuste sobre ese periodo es exploratorio. La evaluación confirmatoria propuesta es una ventana de 12 meses de datos futuros no observados: parámetros, mapeo de estado, escalamiento y umbrales se congelan antes del primer día; se calcula solo filtrado/predictivo; no se reentrena durante la ventana. Una alternativa secundaria es una muestra externa no inspeccionada y comparable, documentada antes de abrirla.

## Criterios de utilidad

Durante la ventana prospectiva se exige cobertura de Modelo B >=95% de fechas elegibles, frecuencia efectiva entre 8% y 12%, y reporte de alertas en fechas con banderas. La métrica primaria propuesta es recall de episodios de caída de 7% en 20 sesiones con alerta en las cinco decisiones previas. Para justificar investigación adicional, B debe superar A en recall por >=10 puntos porcentuales sin aumentar falsas alarmas por más de 2 puntos, con al menos 10 episodios prospectivos. Menos de 10 episodios es INCONCLUSO.

## Decisiones económicas para revisión humana

1. Si 7% en 20 sesiones representa el riesgo que justificaría una revisión humana.
2. Si 10% de alertas es una carga de revisión aceptable.
3. Qué consecuencia humana, no automática, tendría una alerta.
4. Si la disponibilidad antes de abrir `t+1` es aceptable mientras no se verifique.
5. Si el costo de cubrir falsos positivos supera el beneficio potencial de alertar caídas.
6. Si se aprueba esperar una ventana prospectiva nueva antes de afirmar utilidad.

No se entrenarán HMM ni se calcularán resultados hasta aprobar estas decisiones.
