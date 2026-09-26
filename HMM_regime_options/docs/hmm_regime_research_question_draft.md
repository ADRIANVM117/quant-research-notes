# HMM de regímenes — pregunta de investigación borrador

Fecha: 2026-09-26  
Estado: borrador conceptual separado de Checkpoint B. No autoriza entrenamiento.

## Pregunta

¿Un modelo de estados latentes, estimado solo con observaciones disponibles cada día, puede emitir una probabilidad prospectiva de un régimen de riesgo de SPY más útil que una regla simple sin estados latentes?

Un régimen latente de riesgo es una condición no observada directamente que se manifiesta como combinación persistente de retornos, volatilidad realizada y, si se aprueba, skew. No significa causalidad económica, compras institucionales ni orden de operación.

## Observaciones disponibles en `t`

- retorno log de SPY hasta el cierre de `t`;
- volatilidad realizada de una ventana que termina en `t`;
- skew v2 fechado en `t`, solo con par y cotización utilizables, manteniendo banderas de calidad;
- decisión propuesta en `t+1`, bajo el supuesto no verificado de disponibilidad EOD antes de abrir.

No se permiten precios posteriores, etiquetas futuras, estados suavizados ni parámetros elegidos con el periodo evaluado.

## Salida prospectiva

La salida candidata es probabilidad **filtrada** de estado de riesgo, `P(S_t=r | observaciones_<=t)`, o probabilidad de transición `P(S_{t+1}=r | observaciones_<=t)`. Una alerta prospectiva sería una regla preespecificada sobre esa probabilidad, utilizable como pronto en `t+1` bajo el supuesto declarado. Los estados no reciben nombres económicos antes del ajuste.

## Filtrado y suavizado

- Filtrada: usa solo datos hasta `t`; única admisible para alertas históricas prospectivas.
- Suavizada: usa observaciones posteriores a `t`; puede describir retrospectivamente, pero nunca medir anticipación, frecuencia de alertas o desempeño.

Todo reporte debe etiquetar cuál muestra.

## Comparadores mínimos

1. `vol20` de SPY sin opciones.
2. Señal simple de skew preespecificada, si se continúa tras B.
3. Regla de persistencia sin HMM sobre la misma variable observada que alimentaría el HMM.

La comparación debe igualar frecuencia de alertas o usar una curva de operación preespecificada. Segmentación visual no demuestra ventaja.

## Investigación después de conocer 2024–2026

Ya vimos resultados de 2024–2026; no son prueba final intacta para elegir estados, variables, ventanas, umbrales o semillas. Cualquier HMM diseñado con 2020–2026 es exploratorio o desarrollo retrospectivo.

Una evaluación confirmatoria requiere: datos futuros aún no observados con parámetros congelados, una muestra externa no inspeccionada y comparable, o validación anidada declarada exploratoria. La ruta preferida es una ventana prospectiva nueva; ningún ajuste posterior puede presentarse como prueba fuera de muestra.

## Decisiones antes de entrenar

1. Número de estados y justificación, fijados antes de métricas.
2. Variables de emisión, transformaciones, faltantes y papel de skew.
3. Entrenamiento inicial, reentrenamiento y semillas.
4. Probabilidad filtrada o transición, umbral y frecuencia objetivo.
5. Comparadores, métricas y fuente de evaluación prospectiva.
6. Cobertura y banderas de calidad.

Hasta resolverlas, esto es una pregunta de investigación, no un plan de entrenamiento.
