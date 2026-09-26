# HMM_regimen_options

## Pregunta

¿Una señal diaria derivada de opciones de SPY aporta una alerta anticipada
de condiciones de mayor riesgo en el mercado estadounidense, por encima
de una referencia que utiliza únicamente datos del subyacente?

El HMM es un candidato de investigación. Su posible aplicación sería informar
una revisión humana de riesgo y portafolio para el Reto Actinver. El Reto puede
operar sin este proyecto.

## Alcance inicial

- Subyacente inicial: SPY.
- Frecuencia de decisión: diaria, una vez confirmada la disponibilidad de
  los datos de cierre.
- Datos candidatos: retornos diarios de SPY y una medida de skew de opciones
  construida con puts y calls de vencimiento y delta comparables.
- Resultado buscado: una alerta evaluable antes de episodios futuros de riesgo.
- Primeras decisiones: continuar la investigación, mantenerla aislada o
  detenerla por falta de datos o de evidencia incremental.

No se asume que el HMM prediga transiciones, que el skew mida directamente
actividad institucional ni que una señal estadounidense sea útil para todos
los instrumentos del simulador mexicano.

## Checkpoints iniciales

### 1. Viabilidad de datos

Verificar acceso, cobertura histórica, calidad de las cadenas, disponibilidad
de IV y delta, posibilidad de seleccionar contratos comparables y momento
en que la señal estaría disponible.

### 2. Potencial de alerta

Definir el evento futuro y la evaluación temporal antes de inspeccionar
resultados. Comparar una señal sencilla con skew y, si se justifica, un HMM,
contra una referencia basada solo en datos de SPY.

### 3. Posible aplicación al Reto

Solo si los pasos anteriores aportan evidencia, formular una decisión concreta
de riesgo o portafolio que la alerta podría informar. Evaluarla con las
restricciones, costos y precios pertinentes del simulador antes de integrarla.

## Estado

**2026-09-25 — Inicio.** Metodología v1 preparada. No se han auditado cadenas
reales ni evaluado modelos. No existe señal aprobada para Actinver.

La definición operativa y los criterios de decisión están en
[METHODOLOGY.md](METHODOLOGY.md). Las reglas de trabajo para agentes están en
[AGENTS.md](AGENTS.md).