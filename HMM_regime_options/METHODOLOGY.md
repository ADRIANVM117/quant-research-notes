# METHODOLOGY.md — v1

Fecha: 2026-09-25
Estado: diseño inicial; sin datos inspeccionados y sin modelo evaluado.

## 1. Objetivo y límites

Investigar si información diaria de opciones de SPY ayuda a alertar sobre
condiciones futuras de mayor riesgo de mercado. El resultado podría informar
una revisión humana de exposición durante el Reto Actinver, pero este proyecto
permanece independiente hasta superar sus evaluaciones.

El objetivo inicial es decidir si merece más investigación. Dos días de trabajo
no bastan para certificar capacidad predictiva robusta ni para aprobar una
regla de asignación de capital.

## 2. Hipótesis

H1: Una medida comparable y observable de skew de opciones de SPY contiene
información incremental sobre episodios futuros de riesgo, respecto a
variables construidas exclusivamente con precios pasados de SPY.

Hipótesis nula práctica: la información de opciones no mejora de manera
suficiente la anticipación, estabilidad o utilidad de una alerta sencilla.

Un HMM es un método candidato para representar estados latentes y su
persistencia. No forma parte de la hipótesis económica por definición:
si un método más simple responde mejor la pregunta, se conserva el simple.

## 3. Reloj de información

Para cada fecha t, registrar la fecha de la cadena, la fecha del precio de SPY
y el momento comprobable en que ambos datos estuvieron disponibles.

Una señal construida con el cierre de t solo puede evaluarse para decisiones
posteriores a su disponibilidad. Si la disponibilidad histórica exacta no
puede reconstruirse, usar una regla conservadora y declararla como supuesto.

Para alertas históricas usar estimaciones filtradas o predicciones generadas
con información disponible hasta t. No usar estados suavizados calculados con
observaciones posteriores ni parámetros ajustados sobre el periodo de prueba.

## 4. Checkpoint A: auditoría de datos

Comenzar con SPY y una muestra de fechas históricas repartidas entre periodos
de distinta volatilidad. Antes de descargar años completos, comprobar:

- acceso efectivo a HISTORICAL_OPTIONS y a precios diarios de SPY;
- cobertura por fecha y presencia de IV, delta, tipo, strike y vencimiento;
- cotizaciones y campos de liquidez disponibles, y proporción de valores
  inválidos o faltantes;
- posibilidad de encontrar puts cercanos a delta -0.25 y calls cercanos a
  delta +0.25, con vencimiento cercano a 30 días;
- distancia efectiva a las deltas y al vencimiento objetivo;
- saltos de la medida causados por cambios de contratos;
- sincronización de fechas y tratamiento de ajustes del subyacente.

Conservar la respuesta original y registrar, para cada fecha, los contratos
seleccionados, los filtros aplicados y el motivo de exclusión de fechas.
No rellenar fechas sin contratos comparables mediante interpolación silenciosa.

Definición candidata de la variable:

    skew_t = IV_put(-0.25 delta, ~30 DTE)
             - IV_call(+0.25 delta, ~30 DTE)

Es una definición provisional hasta verificar qué precisión permite la cadena
real. Congelar el procedimiento exacto de selección antes de construir la
serie completa y evaluar resultados.

Salida del checkpoint: GO para construir serie / REVISAR definición / STOP
por calidad o acceso insuficiente, con evidencia registrada.

## 5. Checkpoint B: investigación de alerta

Antes de observar desempeño, fijar en un registro de experimento:

1. Evento futuro de riesgo y horizonte de anticipación. Deben poder calcularse
   sin usar información futura en las variables predictoras.
2. Historial, separación cronológica de desarrollo y evaluación final.
3. Variables, transformaciones, tratamiento de faltantes y sus ventanas.
4. Benchmark sin opciones y regla candidata con opciones.
5. Métricas: anticipación, sensibilidad a eventos, falsas alarmas,
   calibración si se producen probabilidades y cobertura de fechas.
6. Regla de decisión para continuar o detenerse.

Evaluar primero si una señal sencilla de skew añade información al benchmark.
Si el resultado lo justifica, estudiar un HMM pequeño. Ajustar parámetros
solo en el periodo de entrenamiento y producir señales históricas mediante
un procedimiento que respete el orden temporal. Registrar todos los intentos.

No asignar nombres económicos a los estados antes del ajuste. Un aumento de
probabilidad de un estado no se interpretará como aviso de transición hasta
demostrar que precede al evento definido.

## 6. Checkpoint C: relevancia para Actinver

Una señal prometedora deberá vincularse con una decisión específica, por
ejemplo revisar nuevas compras o el presupuesto de riesgo. La evaluación
debe considerar:

- si el aviso llega antes del momento real de decisión;
- qué instrumentos del Reto podrían estar expuestos al riesgo señalado;
- precios, liquidez, costos y restricciones del simulador;
- oportunidades perdidas y efectos de falsas alarmas.

No extrapolar automáticamente una señal sobre SPY a fondos mexicanos,
acciones locales o todos los ETFs del SIC. No enviar órdenes automáticas.

## 7. Decisiones

- **STOP por datos:** el acceso o la calidad impiden una serie comparable.
- **STOP por señal:** con datos adecuados, la señal no aporta evidencia
  incremental suficiente frente al benchmark.
- **AISLADO:** hay un resultado interesante, pero falta evidencia de
  anticipación o utilidad para una decisión del Reto.
- **CANDIDATO:** existe evidencia preliminar incremental y una decisión
  factible; continúa bajo observación prospectiva y revisión humana.

El estado CANDIDATO no equivale a aprobación para gestionar posiciones.

## 8. Registro de resultados

Para cada checkpoint guardar: fecha, versión de metodología, muestra,
consultas realizadas, exclusiones, resultados, intentos alternativos,
limitaciones y decisión. Todo cambio posterior a ver resultados genera un
experimento nuevo; no reescribe la hipótesis original.