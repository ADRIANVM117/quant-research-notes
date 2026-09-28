# Precio del straddle ATM de SPY y movimiento futuro

**Estado:** preparación metodológica y auditoría de datos. No existe aún una señal, pago calculado, métrica predictiva ni evaluación de desempeño.

## Pregunta central

¿El costo relativo de un straddle ATM de SPY anticipa el movimiento absoluto de SPY hasta su vencimiento mejor que una estimación basada solo en retornos históricos?

## Hipótesis económica

El precio conjunto de una call y una put del mismo strike y vencimiento puede contener información sobre la magnitud del movimiento futuro que no está completa en los retornos pasados. Tanto el costo del par como el movimiento observado se expresarán respecto al precio de SPY conocido en la fecha de observación.

El precio también refleja plazo, moneyness, tasas, dividendos, liquidez y primas por riesgo. Una relación predictiva no demostraría que negociar el straddle sea rentable.

## Cambio trazable de pregunta

El antecedente de esta fase preguntaba si el costo del straddle informaba mejor la **volatilidad realizada de las próximas 20 sesiones** que `vol20`. Esa pregunta queda descartada para esta fase, sin borrar sus auditorías.

La pregunta actual usa el movimiento absoluto hasta el vencimiento porque corresponde de forma más directa al pago terminal de un straddle que la desviación estándar de veinte retornos diarios. El valor intrínseco al vencimiento no se llamará P&L de una operación real: SPY tiene opciones americanas y las cotizaciones archivadas no prueban ejecución simultánea de call y put.

## Datos y auditorías existentes

Las cadenas originales de SPY permanecen archivadas en `../../HMM_regime_options/data/raw/` y se consultan en modo lectura, sin duplicarlas. La auditoría de pares encontró al menos un straddle candidato de 27–33 DTE en 1,673 de 1,674 sesiones entre 2020-01-02 y 2026-08-31; los 9,282 `contractID` repetidos eran idénticos.

La IV del proveedor no se usará como señal principal: la auditoría mostró una escalera de valores repetidos. Las notebooks y reportes de esas auditorías se conservan.

## Reglas aún abiertas

Antes de cualquier cálculo futuro deben fijarse, sin mirar resultados:

- selección definitiva del par ATM y DTE;
- filtros y tratamiento de spreads;
- construcción del benchmark de retornos históricos para el mismo horizonte hasta vencimiento;
- precio de SPY al vencimiento y reglas para vencimientos sin precio disponible;
- tratamiento de ausencias, duplicados y cambios de vencimiento;
- evaluación y separación temporal, en particular porque 2024–2026 ya fue visto.

## Límites

- La hora de cotización/publicación no es verificable en las cadenas. Usar información de `t` para una decisión posterior en `t+1` sigue siendo un supuesto EOD no verificado.
- Bid y ask archivados no prueban ejecución simultánea ni precios negociables para ambos lados.
- Los archivos originales no se modifican desde este proyecto.
