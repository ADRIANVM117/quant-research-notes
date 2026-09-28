# Precio del straddle ATM de SPY y volatilidad futura

Proyecto de investigación cuantitativa sobre la información contenida en los precios de opciones SPY.

**Estado:** preparación de datos. La hipótesis predictiva aún no se ha evaluado. Este proyecto no es una estrategia de trading ni un backtest de rentabilidad de straddles.

## Pregunta

¿El costo relativo de un straddle ATM de SPY, con vencimiento cercano a 30 días calendario, ordena la volatilidad realizada de las próximas 20 sesiones mejor que `vol20` observada hoy?

Un straddle ATM combina una call y una put del mismo strike y vencimiento. Su costo relativo será el precio conjunto de ambas opciones expresado respecto al precio contemporáneo de SPY. La construcción exacta de esa serie todavía no está fijada.

## Hipótesis económica

Los precios de opciones incorporan el costo que el mercado asigna a movimientos futuros. Por ello, el precio de un straddle cercano al dinero podría contener información sobre volatilidad futura que no está completamente representada en los últimos 20 retornos.

El precio también depende del plazo, la distancia al strike, las tasas, los dividendos y las primas por riesgo. No lo llamaremos volatilidad implícita pura ni interpretaremos un buen resultado predictivo como evidencia de que comprar el straddle sea rentable.

## Datos disponibles

Las cadenas históricas de opciones SPY proceden de Alpha Vantage y están archivadas en `HMM_regime_options/data/raw/`. Este proyecto las consulta sin duplicarlas; `docs/data_inventory.md` documenta las rutas y su procedencia.

La auditoría registró 1,674 sesiones entre 2020-01-02 y 2026-08-31. La auditoría de pares call–put reportó al menos un straddle candidato con vencimiento de 27–33 días en 1,673 sesiones. Esos conteos demuestran cobertura inicial de datos, no capacidad predictiva.

Se reportaron 9,282 registros repetidos por `contractID` dentro de sus sesiones; todos eran idénticos. La construcción reproducible deberá documentar su eliminación.

## Por qué cambió el alcance

La primera pregunta del proyecto se refería a la volatilidad implícita (IV) cercana a 30 días. Sin embargo, una sonda de 343,228 contratos únicos mostró solo 89 valores distintos de IV proporcionada por el proveedor. Esa resolución no se aceptó sin más como señal principal.

Reconstruir IV históricamente desde bid/ask quedó pendiente porque faltan tasas y dividendos futuros conocidos en cada fecha de observación para un tratamiento adecuado de las opciones SPY de ejercicio americano. Conservamos esas auditorías en `docs/`; el nuevo objeto de estudio es el precio observado del par call–put.

## Siguiente entregable

Una notebook ejecutada mostrará pares identificables por fecha y `contractID`, su cercanía ATM, vencimiento, bid/ask, punto medio y spreads. Los cálculos reutilizables estarán en scripts; la notebook mostrará código ejecutado, resultados, interpretación y espacio para notas del investigador.

Antes de evaluar la hipótesis deben fijarse la regla exacta de selección del par, el control de spreads, el tratamiento de fechas sin par, la construcción de la variable futura y la comparación con `vol20`. Todavía no existe una serie diaria definitiva ni resultados predictivos para este proyecto.

## Límites

- Las cadenas tienen fecha, pero no una hora verificable de cotización o publicación. Usarlas para una decisión en la siguiente sesión supone disponibilidad EOD aún no verificada.
- Bid y ask archivados no demuestran que call y put pudieran negociarse simultáneamente a esos precios.
- El periodo 2024–2026 ya fue examinado en el proyecto HMM anterior. Una evaluación histórica aquí no debe presentarse como confirmación prospectiva intacta.
- Las reglas de construcción y evaluación deberán registrarse antes de mirar el resultado predictivo. La ausencia de evidencia favorable también será un resultado del proyecto.

## Organización

- `docs/data_inventory.md`: rutas y procedencia de datos.
- `docs/`: auditorías de factibilidad y de resolución de IV.
- `scripts/`: cálculos reproducibles.
- `notebooks/`: código ejecutado, resultados visibles e interpretación.

Los archivos originales de opciones permanecen fuera de esta carpeta. Cualquier reproducción deberá indicar su ubicación local.