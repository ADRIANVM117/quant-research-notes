# AGENTS.md — HMM_regimen_options

## Propósito

Este repositorio investiga si datos diarios de opciones estadounidenses aportan
una alerta anticipada de cambios hacia condiciones de mayor riesgo de mercado.

Es un proyecto independiente. Su posible uso en el Reto Actinver es una hipótesis
de aplicación, no una integración aprobada ni una dependencia operativa.

## Reglas de investigación

1. Antes de ejecutar un experimento, registrar la hipótesis, la definición del
   evento futuro, los datos disponibles al momento de la señal, el método,
   el benchmark, las métricas y los criterios de decisión.
2. Distinguir explícitamente entre:
   - probabilidad filtrada: estimada con información disponible hasta la fecha t;
   - estado suavizado: estimado usando también observaciones posteriores a t.
   Nunca evaluar una alerta histórica con estados suavizados.
3. Ajustar transformaciones, parámetros, selección de variables y umbrales
   únicamente con el periodo de desarrollo correspondiente. Respetar el orden
   temporal en toda evaluación.
4. Registrar cada variante y cada intento. No presentar el mejor resultado de
   varias pruebas como si hubiera sido la única hipótesis.
5. Comparar cualquier HMM con una referencia sencilla que no use opciones.
   Una segmentación visualmente convincente no demuestra anticipación ni
   utilidad para decisiones de inversión.
6. Separar tres conclusiones: calidad de datos, capacidad de alerta y utilidad
   para una decisión concreta del Reto Actinver.
7. No atribuir a la IV o al skew una causa económica específica, como compras
   institucionales de protección, sin evidencia adicional.
8. Conservar datos originales y trazabilidad de la selección de contratos.
   Nunca reemplazar silenciosamente observaciones faltantes o inválidas.
9. Mantener secretos fuera de código, salidas, documentación y commits.
   Leer ALPHAVANTAGE_API_KEY desde el entorno; no imprimir su valor.
10. No automatizar acciones dentro del simulador Actinver. Cualquier eventual
    salida operativa de este proyecto requiere revisión humana y validación
    independiente de las reglas y precios del simulador.

## Forma de trabajo

Priorizar el checkpoint más pequeño que pueda refutar la viabilidad del
proyecto. Documentar resultados negativos y limitaciones. Antes de ampliar
símbolos, variables o complejidad del modelo, justificar qué pregunta nueva
responde la ampliación.

No modificar la metodología congelada de un experimento después de observar
sus resultados. Si hace falta cambiarla, registrar una nueva versión y tratar
la prueba anterior como exploratoria.